import json
import time

import openai
import tiktoken
from flask import current_app

from .openai_client import OpenAIClient
from .result_cache import ResultCache


class AIModerator:
    """Handles different AI moderation strategies"""

    def __init__(self):
        self.client_manager = OpenAIClient()
        self.cache = ResultCache()
        # Load model and token settings from config
        cfg = current_app.config
        self.model_name = cfg.get('OPENAI_CHAT_MODEL', 'gpt-5-2025-08-07')
        self.model_context_window = int(
            cfg.get('OPENAI_CONTEXT_WINDOW', 272000))
        self.max_output_tokens = int(
            cfg.get('OPENAI_MAX_OUTPUT_TOKENS', 500))

        # Initialize tokenizer; prefer model-specific, fallback to cl100k_base
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.model_name)
        except (KeyError, ValueError):
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text):
        """Count the number of tokens in a text string"""
        try:
            return len(self.tokenizer.encode(text))
        except (UnicodeDecodeError, ValueError, TypeError) as e:
            current_app.logger.error(f"Token counting error: {str(e)}")
            # Fallback: rough estimation (1 token ≈ 4 characters)
            return len(text) // 4

    def calculate_max_content_tokens(self, custom_prompt=None):
        """
        Calculate the maximum tokens available for content based on prompt size.
        Dynamically adjusts for custom prompts to prevent exceeding context window.
        Uses conservative estimates to account for tokenizer inaccuracies.
        """
        # Calculate custom prompt tokens if provided
        prompt_tokens = 0
        if custom_prompt:
            # Account for the full prompt template
            system_message = (
                """You are a content moderator. Analyze if content violates the given rule. """
                """Be conservative - when in doubt, approve.\n\n"""
                """Respond ONLY with JSON:\n"""
                """{"decision": "approved|rejected", "reason": "brief explanation", "confidence": 0.85}"""
            )
            user_template = f"""RULE: {custom_prompt}

CONTENT: {{content}}

Does content violate this rule? JSON only:"""
            # Count tokens for the prompt parts (excluding content placeholder)
            prompt_tokens = self.count_tokens(system_message) + self.count_tokens(user_template)

            # Log large prompts for debugging
            if prompt_tokens > 10000:
                current_app.logger.warning(
                    f"Large custom prompt detected: {prompt_tokens} tokens. "
                    f"This will significantly reduce available content space."
                )
        else:
            # For default moderation, estimate prompt overhead
            prompt_tokens = 150  # Typical system + user message without content

        # Total overhead = prompt + output tokens + larger buffer for safety
        # Add 15% buffer to prompt tokens to account for tokenizer inaccuracies
        # (being extra conservative for large prompts)
        safe_prompt_tokens = int(prompt_tokens * 1.15)
        total_overhead = safe_prompt_tokens + self.max_output_tokens + 500  # 500 for message structure overhead

        # Use VERY conservative safety margin (70%) to account for tokenizer differences
        # between our counting and OpenAI's counting. Better to chunk more than fail.
        safety_margin = 0.70

        available_for_content = int(
            (self.model_context_window - total_overhead) * safety_margin)

        # Hard cap: never allow more than 180k tokens for content
        # This ensures we stay well under the 272k limit even with large prompts
        available_for_content = min(available_for_content, 180000)

        # Ensure a sensible lower bound
        available_for_content = max(12000, available_for_content)
        return available_for_content

    def split_text_into_chunks(self, text, max_tokens_per_chunk):
        """
        Split text into chunks that fit within token limits.
        Tries to split at sentence boundaries when possible.
        """
        # If text fits within limit, return as single chunk
        total_tokens = self.count_tokens(text)
        if total_tokens <= max_tokens_per_chunk:
            return [text]

        chunks = []
        current_chunk = ""

        # Split by paragraphs first, then sentences
        paragraphs = text.split('\n\n')

        for paragraph in paragraphs:
            # If current chunk + paragraph would exceed limit, finalize current chunk
            temp_chunk = current_chunk + \
                ("\n\n" if current_chunk else "") + paragraph
            if current_chunk and self.count_tokens(temp_chunk) > max_tokens_per_chunk:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    # Single paragraph is too large, split by sentences
                    chunks.extend(self._split_paragraph_by_sentences(
                        paragraph, max_tokens_per_chunk))
            else:
                current_chunk = temp_chunk

        # Add the final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _split_paragraph_by_sentences(self, paragraph, max_tokens_per_chunk):
        """Split a large paragraph by sentences"""
        import re

        # Split by sentence endings
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            temp_chunk = current_chunk + \
                (" " if current_chunk else "") + sentence
            if current_chunk and self.count_tokens(temp_chunk) > max_tokens_per_chunk:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # Single sentence is too large, split by words (last resort)
                    chunks.extend(self._split_sentence_by_words(
                        sentence, max_tokens_per_chunk))
            else:
                current_chunk = temp_chunk

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _split_sentence_by_words(self, sentence, max_tokens_per_chunk):
        """Split a very long sentence by words as last resort"""
        words = sentence.split()
        chunks = []
        current_chunk = ""

        for word in words:
            temp_chunk = current_chunk + (" " if current_chunk else "") + word
            if current_chunk and self.count_tokens(temp_chunk) > max_tokens_per_chunk:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = word
                else:
                    # Even single word is too large (very rare), just add it
                    chunks.append(word)
                    current_chunk = ""
            else:
                current_chunk = temp_chunk

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _combine_chunk_results(self, chunk_results, original_content_length):
        """
        Combine results from multiple chunks.
        If ANY chunk is rejected, the entire content is rejected.
        """
        if not chunk_results:
            return {
                'decision': 'rejected',
                'reason': 'No moderation results available',
                'confidence': 0.0,
                'moderator_type': 'ai',
                'categories': {'error': True},
                'category_scores': {'error': 1.0},
                'openai_flagged': False
            }

        # Check if any chunk was rejected
        rejected_chunks = [
            r for r in chunk_results if r['decision'] == 'rejected']

        if rejected_chunks:
            # If any chunk is rejected, reject the entire content
            # Use the result with highest confidence among rejected chunks
            primary_rejection = max(
                rejected_chunks, key=lambda x: x.get('confidence', 0))

            # Combine categories and scores from all rejected chunks
            combined_categories = {}
            combined_scores = {}

            for result in rejected_chunks:
                if 'categories' in result:
                    combined_categories.update(result['categories'])
                if 'category_scores' in result:
                    combined_scores.update(result['category_scores'])

            return {
                'decision': 'rejected',
                'reason': (f"Content rejected (analyzed {len(chunk_results)} chunks, "
                           f"{len(rejected_chunks)} flagged): {primary_rejection['reason']}"),
                'confidence': primary_rejection.get('confidence', 0.8),
                'moderator_type': primary_rejection.get('moderator_type', 'ai'),
                'categories': combined_categories,
                'category_scores': combined_scores,
                'openai_flagged': primary_rejection.get('openai_flagged', False),
                'chunk_count': len(chunk_results),
                'rejected_chunks': len(rejected_chunks),
                'original_length': original_content_length
            }
        else:
            # All chunks approved - approve the entire content
            # Use average confidence
            avg_confidence = sum(r.get('confidence', 0.8)
                                 for r in chunk_results) / len(chunk_results)

            return {
                'decision': 'approved',
                'reason': f"All {len(chunk_results)} content chunks passed moderation",
                'confidence': avg_confidence,
                'moderator_type': chunk_results[0].get('moderator_type', 'ai'),
                'categories': {},
                'category_scores': {},
                'openai_flagged': False,
                'chunk_count': len(chunk_results),
                'rejected_chunks': 0,
                'original_length': original_content_length
            }

    def moderate_content(self, content, content_type='text', custom_prompt=None):
        """
        Moderate content using a multi-layered approach with chunking for large content:
        1. Custom prompt analysis (for specific rules) - if provided
        2. OpenAI's built-in moderation API (fast baseline safety check)
        3. Enhanced default moderation (comprehensive safety check)
        """
        try:
            # Check if OpenAI API key is available
            if not self.client_manager.is_configured():
                return {
                    'decision': 'rejected',
                    'reason': 'OpenAI API key not configured - content rejected',
                    'confidence': 0.0,
                    'moderator_type': 'ai',
                    'categories': {'configuration_error': True},
                    'category_scores': {'configuration_error': 1.0},
                    'openai_flagged': False
                }

            # Check content size and split if necessary
            content_tokens = self.count_tokens(content)

            # STEP 1: If custom prompt is provided, use ONLY custom prompt analysis
            if custom_prompt:
                # Calculate max content tokens based on custom prompt size
                max_content_tokens = self.calculate_max_content_tokens(custom_prompt)
                current_app.logger.info(
                    f"Content has {content_tokens} tokens, max allowed: {max_content_tokens}")

                if content_tokens <= max_content_tokens:
                    return self._analyze_with_custom_prompt(content, custom_prompt)
                else:
                    # Split content and analyze each chunk
                    chunks = self.split_text_into_chunks(content, max_content_tokens)
                    current_app.logger.info(
                        f"Split content into {len(chunks)} chunks for custom prompt analysis")

                    chunk_results = []
                    for i, chunk in enumerate(chunks):
                        result = self._analyze_with_custom_prompt(
                            chunk, custom_prompt)
                        chunk_results.append(result)

                        # Early exit if chunk is rejected (for efficiency)
                        if result['decision'] == 'rejected':
                            break

                    return self._combine_chunk_results(chunk_results, len(content))

            # STEP 2: For default moderation, run baseline check first
            # Note: OpenAI moderation API has its own limits, but typically handles larger content
            current_app.logger.info(f"Content has {content_tokens} tokens")
            baseline_result = self._run_baseline_moderation(content)
            if baseline_result['decision'] == 'rejected':
                return baseline_result

            # STEP 3: Run enhanced default moderation for comprehensive safety
            # Calculate max content tokens for default moderation (no custom prompt)
            max_content_tokens = self.calculate_max_content_tokens()

            if content_tokens <= max_content_tokens:
                return self._run_enhanced_default_moderation(content)
            else:
                # Split content and analyze each chunk
                chunks = self.split_text_into_chunks(content, max_content_tokens)
                current_app.logger.info(
                    f"Split content into {len(chunks)} chunks for enhanced moderation")

                chunk_results = []
                for i, chunk in enumerate(chunks):
                    result = self._run_enhanced_default_moderation(chunk)
                    chunk_results.append(result)

                    # Early exit if chunk is rejected (for efficiency)
                    if result['decision'] == 'rejected':
                        break

                return self._combine_chunk_results(chunk_results, len(content))

        except (openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError) as e:
            current_app.logger.error(f"OpenAI API connection error after retries: {str(e)}")
            return {
                'decision': 'approved',
                'reason': f'OpenAI API unavailable after retries - approved for manual review. Error: {str(e)[:100]}',
                'confidence': 0.0,
                'moderator_type': 'ai',
                'categories': {'api_connection_error': True},
                'category_scores': {'api_connection_error': 1.0},
                'openai_flagged': False
            }
        except (openai.OpenAIError, openai.APIError, openai.RateLimitError) as e:
            current_app.logger.error(f"OpenAI API error: {str(e)}")
            return {
                'decision': 'approved',
                'reason': f'OpenAI API error - approved for manual review. Error: {str(e)[:100]}',
                'confidence': 0.0,
                'moderator_type': 'ai',
                'categories': {'api_error': True},
                'category_scores': {'api_error': 1.0},
                'openai_flagged': False
            }
        except (ValueError, TypeError, KeyError) as e:
            current_app.logger.error(f"Data processing error in moderation: {str(e)}")
            return {
                'decision': 'rejected',
                'reason': f'Content processing error: {str(e)}',
                'confidence': 0.0,
                'moderator_type': 'ai',
                'categories': {},
                'category_scores': {},
                'openai_flagged': False
            }

    def _retry_api_call(self, api_function, max_retries=3, initial_delay=1.0):
        """Retry API calls with exponential backoff for transient errors"""
        last_exception = None

        for attempt in range(max_retries):
            try:
                return api_function()
            except (openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    error_type = type(e).__name__
                    current_app.logger.warning(
                        f"OpenAI API {error_type} (attempt {attempt + 1}/{max_retries}): {str(e)}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    current_app.logger.error(
                        f"OpenAI API failed after {max_retries} attempts: {str(e)}"
                    )
            except (openai.OpenAIError, openai.APIError, openai.RateLimitError):
                # Don't retry on other API errors (auth, rate limit, etc.)
                raise

        # If we exhausted all retries, raise the last exception
        raise last_exception

    def _analyze_with_custom_prompt(self, content, custom_prompt):
        """Use GPT with custom prompts for specialized moderation rules"""
        try:
            # Check cache first
            cache_key = self.cache.generate_cache_key(content, custom_prompt)
            cached_result = self.cache.get_cached_result(cache_key)
            if cached_result:
                return cached_result

            system_message = (
                """You are a content moderator. Analyze if content violates the given rule. """
                """Be conservative - when in doubt, approve.\n\n"""
                """Respond ONLY with JSON:\n"""
                """{"decision": "approved|rejected", "reason": "brief explanation", "confidence": 0.85}"""
            )

            user_message = f"""RULE: {custom_prompt}

CONTENT: {content}

Does content violate this rule? JSON only:"""

            # Wrap API call with retry logic
            def make_api_call():
                client = self.client_manager.get_client()
                return client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message}
                    ],
                    top_p=1.0,       # Optimize for speed
                    frequency_penalty=0,
                    presence_penalty=0
                )

            response = self._retry_api_call(make_api_call)

            result_text = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                result = json.loads(result_text)

                # Validate required fields
                if 'decision' not in result or result['decision'] not in ['approved', 'rejected']:
                    result['decision'] = 'approved'  # Default to approve if unclear

                if 'confidence' not in result or not isinstance(result['confidence'], (int, float)):
                    result['confidence'] = 0.3  # Low confidence for malformed response

                if 'reason' not in result:
                    result['reason'] = 'Malformed AI response - defaulting to approval'

                # Apply confidence threshold - reject only if sufficiently confident
                MIN_CONFIDENCE_FOR_REJECTION = 0.55
                if result['decision'] == 'rejected' and result['confidence'] < MIN_CONFIDENCE_FOR_REJECTION:
                    result['decision'] = 'approved'
                    result['reason'] = (f"Low confidence rejection ({result['confidence']:.2f} < "
                                        f"{MIN_CONFIDENCE_FOR_REJECTION}) - approved instead. "
                                        f"Original reason: {result['reason']}")

                # Add metadata
                result['moderator_type'] = 'ai'
                result['categories'] = {
                    'custom_rule': result['decision'] != 'approved'}
                result['category_scores'] = {
                    'custom_rule': result['confidence']}
                result['openai_flagged'] = False

                # Cache the result
                self.cache.cache_result(cache_key, result)

                return result

            except json.JSONDecodeError:
                # Fallback parsing if JSON is malformed - be conservative and approve
                current_app.logger.warning(f"Malformed JSON from AI: {result_text}")
                result_lower = result_text.lower()

                # Only reject if there's a clear rejection signal AND high confidence indicators
                if ('rejected' in result_lower or 'reject' in result_lower) and any(
                        word in result_lower for word in ['explicit', 'inappropriate', 'harmful', 'violates']):
                    decision = 'rejected'
                    confidence = 0.6  # Lower confidence for malformed responses
                else:
                    decision = 'approved'  # Default to approve when unclear
                    confidence = 0.3

                # Apply confidence threshold even for fallback parsing
                MIN_CONFIDENCE_FOR_REJECTION = 0.55
                if decision == 'rejected' and confidence < MIN_CONFIDENCE_FOR_REJECTION:
                    decision = 'approved'
                    reason = (f"Malformed AI response with low confidence ({confidence:.2f}) - "
                              f"approved. Raw response: {result_text[:100]}")
                else:
                    reason = f"Parsed from malformed response: {result_text[:200]}"

                return {
                    'decision': decision,
                    'reason': reason,
                    'confidence': confidence,
                    'moderator_type': 'ai',
                    'categories': {'custom_rule': decision != 'approved'},
                    'category_scores': {'custom_rule': 0.7},
                    'openai_flagged': False
                }

        except (openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError) as e:
            # Connection errors after retry - approve with low confidence for manual review
            current_app.logger.error(f"OpenAI API connection failed in custom prompt after retries: {str(e)}")
            return {
                'decision': 'approved',
                'reason': f'OpenAI API unavailable after retries - approved for manual review. Error: {str(e)[:100]}',
                'confidence': 0.0,
                'moderator_type': 'ai',
                'categories': {'api_connection_error': True},
                'category_scores': {'api_connection_error': 1.0},
                'openai_flagged': False
            }
        except (openai.OpenAIError, openai.APIError, openai.RateLimitError) as e:
            # Other API errors - reject with low confidence for manual review
            current_app.logger.error(f"OpenAI API error in custom prompt: {str(e)}")
            return {
                'decision': 'approved',
                'reason': f'OpenAI API error - approved for manual review. Error: {str(e)[:100]}',
                'confidence': 0.0,
                'moderator_type': 'ai',
                'categories': {'api_error': True},
                'category_scores': {'api_error': 1.0},
                'openai_flagged': False
            }
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as e:
            current_app.logger.error(f"Data processing error in custom prompt: {str(e)}")
            return {
                'decision': 'rejected',
                'reason': f'Content processing error: {str(e)}',
                'confidence': 0.0,
                'moderator_type': 'ai',
                'categories': {'error': True},
                'category_scores': {'error': 1.0},
                'openai_flagged': False
            }

    def _run_baseline_moderation(self, content):
        """Run OpenAI's built-in moderation API for fast baseline safety check"""
        try:
            # Wrap API call with retry logic
            def make_api_call():
                client = self.client_manager.get_client()
                return client.moderations.create(input=content)

            response = self._retry_api_call(make_api_call)
            result = response.results[0]

            if result.flagged:
                # Find the highest scoring category
                categories = result.categories
                category_scores = result.category_scores

                flagged_categories = []
                max_score = 0
                max_category = 'unknown'

                # Check each category attribute
                category_names = ['hate', 'hate/threatening', 'harassment', 'harassment/threatening',
                                  'self-harm', 'self-harm/intent', 'self-harm/instructions', 'sexual',
                                  'sexual/minors', 'violence', 'violence/graphic']

                for category in category_names:
                    if hasattr(categories, category.replace('-', '_').replace('/', '_')):
                        attr_name = category.replace(
                            '-', '_').replace('/', '_')
                        if getattr(categories, attr_name, False):
                            flagged_categories.append(category)
                            score = getattr(category_scores, attr_name, 0)
                            if score > max_score:
                                max_score = score
                                max_category = category

                return {
                    'decision': 'rejected',
                    'reason': f'Content flagged by OpenAI moderation API for: {", ".join(flagged_categories)}',
                    'confidence': max_score,
                    'moderator_type': 'ai',
                    'categories': {cat: True for cat in flagged_categories},
                    'category_scores': {
                        cat: getattr(category_scores, cat.replace('-', '_').replace('/', '_'), 0)
                        for cat in flagged_categories
                    },
                    'openai_flagged': True,
                    'flagged_categories': flagged_categories,
                    'primary_category': max_category
                }
            else:
                # Passed baseline check, continue to next layer
                return {
                    'decision': 'approved',
                    'reason': 'Passed OpenAI baseline moderation',
                    'confidence': 0.8,
                    'moderator_type': 'ai',
                    'categories': {},
                    'category_scores': {},
                    'openai_flagged': False
                }

        except (openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError) as e:
            # Connection errors after retry - continue to next moderation layer
            current_app.logger.warning(f"OpenAI baseline moderation unavailable after retries: {str(e)}")
            return {
                'decision': 'approved',
                'reason': 'OpenAI baseline moderation unavailable - continuing to next check',
                'confidence': 0.0,
                'moderator_type': 'ai',
                'categories': {'api_connection_error': True},
                'category_scores': {'api_connection_error': 0.0},
                'openai_flagged': False
            }
        except (openai.OpenAIError, openai.APIError, openai.RateLimitError) as e:
            # Other API errors - continue to next moderation layer
            current_app.logger.warning(f"OpenAI baseline moderation error: {str(e)}")
            return {
                'decision': 'approved',
                'reason': 'OpenAI baseline moderation error - continuing to next check',
                'confidence': 0.0,
                'moderator_type': 'ai',
                'categories': {'api_error': True},
                'category_scores': {'api_error': 0.0},
                'openai_flagged': False
            }
        except (ValueError, TypeError, AttributeError) as e:
            current_app.logger.error(f"Data processing error in baseline moderation: {str(e)}")
            return {
                'decision': 'rejected',
                'reason': f'Content processing error: {str(e)}',
                'confidence': 0.0,
                'moderator_type': 'ai',
                'categories': {'error': True},
                'category_scores': {'error': 1.0},
                'openai_flagged': False
            }

    def _run_enhanced_default_moderation(self, content):
        """Run enhanced default moderation with comprehensive safety checks"""
        try:
            # Check cache first
            cache_key = self.cache.generate_cache_key(
                content, "enhanced_default")
            cached_result = self.cache.get_cached_result(cache_key)
            if cached_result:
                return cached_result

            system_message = (
                """You are a safety moderator. Reject harmful content: """
                """NSFW, violence, hate speech, illegal activities, self-harm, spam.\n\n"""
                """JSON only:\n"""
                """{"decision": "approved|rejected", "reason": "brief explanation", "confidence": 0.95}"""
            )

            user_message = f"""CONTENT: {content}

Is this harmful? JSON only:"""

            # Wrap API call with retry logic
            def make_api_call():
                client = self.client_manager.get_client()
                return client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message}
                    ],
                    top_p=1.0,
                    frequency_penalty=0,
                    presence_penalty=0
                )

            response = self._retry_api_call(make_api_call)

            result_text = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                result = json.loads(result_text)

                # Validate required fields
                if 'decision' not in result or result['decision'] not in ['approved', 'rejected']:
                    # Default to reject if unclear
                    result['decision'] = 'rejected'

                if 'confidence' not in result or not isinstance(result['confidence'], (int, float)):
                    result['confidence'] = 0.8

                if 'reason' not in result:
                    result['reason'] = 'Enhanced AI safety analysis completed'

                # Add metadata
                result['moderator_type'] = 'ai'
                result['categories'] = {
                    'enhanced_safety': result['decision'] != 'approved'}
                result['category_scores'] = {
                    'enhanced_safety': result['confidence']}
                result['openai_flagged'] = False

                # Cache the result
                self.cache.cache_result(cache_key, result)

                return result

            except json.JSONDecodeError:
                # Fallback parsing - be conservative
                result_lower = result_text.lower()
                if 'approved' in result_lower and 'reject' not in result_lower:
                    decision = 'approved'
                else:
                    decision = 'rejected'  # Default to reject if unclear

                return {
                    'decision': decision,
                    'reason': result_text[:200],
                    'confidence': 0.8,
                    'moderator_type': 'ai',
                    'categories': {'enhanced_safety': decision != 'approved'},
                    'category_scores': {'enhanced_safety': 0.8},
                    'openai_flagged': False
                }

        except (openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError) as e:
            # Connection errors after retry - approve with low confidence for manual review
            current_app.logger.error(f"OpenAI enhanced moderation unavailable after retries: {str(e)}")
            return {
                'decision': 'approved',
                'reason': f'OpenAI API unavailable after retries - approved for manual review. Error: {str(e)[:100]}',
                'confidence': 0.0,
                'moderator_type': 'ai',
                'categories': {'api_connection_error': True},
                'category_scores': {'api_connection_error': 1.0},
                'openai_flagged': False
            }
        except (openai.OpenAIError, openai.APIError, openai.RateLimitError) as e:
            # Other API errors - approve with low confidence for manual review
            current_app.logger.error(f"OpenAI API error in enhanced moderation: {str(e)}")
            return {
                'decision': 'approved',
                'reason': f'OpenAI API error - approved for manual review. Error: {str(e)[:100]}',
                'confidence': 0.0,
                'moderator_type': 'ai',
                'categories': {'api_error': True},
                'category_scores': {'api_error': 1.0},
                'openai_flagged': False
            }
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as e:
            current_app.logger.error(f"Data processing error in enhanced moderation: {str(e)}")
            return {
                'decision': 'rejected',
                'reason': f'Content processing error: {str(e)}',
                'confidence': 0.0,
                'moderator_type': 'ai',
                'categories': {'error': True},
                'category_scores': {'error': 1.0},
                'openai_flagged': False
            }
