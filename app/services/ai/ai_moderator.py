import json
import tiktoken
from flask import current_app
from .openai_client import OpenAIClient
from .result_cache import ResultCache

class AIModerator:
    """Handles different AI moderation strategies"""
    
    def __init__(self):
        self.client_manager = OpenAIClient()
        self.cache = ResultCache()
        # Initialize tokenizer for GPT-3.5 turbo
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except Exception:
            # Fallback to cl100k_base encoding if model-specific encoding fails
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Reserve tokens for system message, user message template, and response
        # GPT-3.5 turbo has 16,385 tokens total
        self.max_content_tokens = 12000  # Conservative limit leaving room for prompts and response
    
    def count_tokens(self, text):
        """Count the number of tokens in a text string"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            current_app.logger.error(f"Token counting error: {str(e)}")
            # Fallback: rough estimation (1 token ≈ 4 characters)
            return len(text) // 4
    
    def split_text_into_chunks(self, text, max_tokens_per_chunk=None):
        """
        Split text into chunks that fit within token limits.
        Tries to split at sentence boundaries when possible.
        """
        if max_tokens_per_chunk is None:
            max_tokens_per_chunk = self.max_content_tokens
            
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
            temp_chunk = current_chunk + ("\n\n" if current_chunk else "") + paragraph
            if current_chunk and self.count_tokens(temp_chunk) > max_tokens_per_chunk:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    # Single paragraph is too large, split by sentences
                    chunks.extend(self._split_paragraph_by_sentences(paragraph, max_tokens_per_chunk))
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
            temp_chunk = current_chunk + (" " if current_chunk else "") + sentence
            if current_chunk and self.count_tokens(temp_chunk) > max_tokens_per_chunk:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # Single sentence is too large, split by words (last resort)
                    chunks.extend(self._split_sentence_by_words(sentence, max_tokens_per_chunk))
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
        rejected_chunks = [r for r in chunk_results if r['decision'] == 'rejected']
        
        if rejected_chunks:
            # If any chunk is rejected, reject the entire content
            # Use the result with highest confidence among rejected chunks
            primary_rejection = max(rejected_chunks, key=lambda x: x.get('confidence', 0))
            
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
                'reason': f"Content rejected (analyzed {len(chunk_results)} chunks, {len(rejected_chunks)} flagged): {primary_rejection['reason']}",
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
            avg_confidence = sum(r.get('confidence', 0.8) for r in chunk_results) / len(chunk_results)
            
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
            
            # Check content size and split if necessary (only log for default moderation or first custom rule)
            content_tokens = self.count_tokens(content)
            if not custom_prompt:
                # Only log token count for default moderation (non-rule based)
                current_app.logger.info(f"Content has {content_tokens} tokens")
            
            # STEP 1: If custom prompt is provided, use ONLY custom prompt analysis
            if custom_prompt:
                if content_tokens <= self.max_content_tokens:
                    return self._analyze_with_custom_prompt(content, custom_prompt)
                else:
                    # Split content and analyze each chunk
                    chunks = self.split_text_into_chunks(content)
                    current_app.logger.info(f"Split content into {len(chunks)} chunks for custom prompt analysis")
                    
                    chunk_results = []
                    for i, chunk in enumerate(chunks):
                        current_app.logger.info(f"Analyzing chunk {i+1}/{len(chunks)} ({self.count_tokens(chunk)} tokens)")
                        result = self._analyze_with_custom_prompt(chunk, custom_prompt)
                        chunk_results.append(result)
                        
                        # Early exit if chunk is rejected (for efficiency)
                        if result['decision'] == 'rejected':
                            current_app.logger.info(f"Chunk {i+1} rejected, stopping analysis")
                            break
                    
                    return self._combine_chunk_results(chunk_results, len(content))
            
            # STEP 2: For default moderation, run baseline check first
            # Note: OpenAI moderation API has its own limits, but typically handles larger content
            baseline_result = self._run_baseline_moderation(content)
            if baseline_result['decision'] == 'rejected':
                return baseline_result
                
            # STEP 3: Run enhanced default moderation for comprehensive safety
            if content_tokens <= self.max_content_tokens:
                return self._run_enhanced_default_moderation(content)
            else:
                # Split content and analyze each chunk
                chunks = self.split_text_into_chunks(content)
                current_app.logger.info(f"Split content into {len(chunks)} chunks for enhanced moderation")
                
                chunk_results = []
                for i, chunk in enumerate(chunks):
                    current_app.logger.info(f"Analyzing chunk {i+1}/{len(chunks)} ({self.count_tokens(chunk)} tokens)")
                    result = self._run_enhanced_default_moderation(chunk)
                    chunk_results.append(result)
                    
                    # Early exit if chunk is rejected (for efficiency)
                    if result['decision'] == 'rejected':
                        current_app.logger.info(f"Chunk {i+1} rejected, stopping analysis")
                        break
                
                return self._combine_chunk_results(chunk_results, len(content))
                    
        except Exception as e:
            current_app.logger.error(f"OpenAI moderation error: {str(e)}")
            return {
                'decision': 'rejected',
                'reason': f'Moderation service error: {str(e)}',
                'confidence': 0.0,
                'moderator_type': 'ai',
                'categories': {},
                'category_scores': {},
                'openai_flagged': False
            }

    def _analyze_with_custom_prompt(self, content, custom_prompt):
        """Use GPT with custom prompts for specialized moderation rules"""
        try:
            # Check cache first
            cache_key = self.cache.generate_cache_key(content, custom_prompt)
            cached_result = self.cache.get_cached_result(cache_key)
            if cached_result:
                return cached_result
                
            system_message = """You are a precise content moderator. Analyze content based on specific rules provided.

IMPORTANT: Only reject content that CLEARLY and SPECIFICALLY violates the given rule. If content doesn't clearly match the rule criteria, approve it. Be conservative - when in doubt, approve.

Respond with ONLY a JSON object in this exact format:
{
    "decision": "approved|rejected",
    "reason": "Brief explanation of your decision",
    "confidence": 0.85
}

- decision: "approved" (content is acceptable) or "rejected" (content clearly violates the specific rule)
- reason: Brief explanation of why you made this decision
- confidence: Number between 0.0 and 1.0 indicating how confident you are
"""
            
            user_message = f"""Analyze this content based on the following specific rule:

RULE: {custom_prompt}

CONTENT: {content}

Determine if the content specifically violates this rule. Be precise and only reject content that clearly matches the rule criteria. If the content doesn't clearly violate this specific rule, approve it.

Respond with ONLY a JSON object in this exact format:
{{
    "decision": "approved|rejected",
    "reason": "Brief explanation of your decision",
    "confidence": 0.85
}}"""
            
            client = self.client_manager.get_client()
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # Much faster than GPT-4
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=150,  # Reduced tokens for faster response
                temperature=0.0,  # Deterministic responses
                top_p=1.0,       # Optimize for speed
                frequency_penalty=0,
                presence_penalty=0
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                result = json.loads(result_text)
                
                # Validate required fields
                if 'decision' not in result or result['decision'] not in ['approved', 'rejected']:
                    result['decision'] = 'rejected'
                
                if 'confidence' not in result or not isinstance(result['confidence'], (int, float)):
                    result['confidence'] = 0.5
                
                if 'reason' not in result:
                    result['reason'] = 'Custom AI analysis completed'
                
                # Add metadata
                result['moderator_type'] = 'ai'
                result['categories'] = {'custom_rule': result['decision'] != 'approved'}
                result['category_scores'] = {'custom_rule': result['confidence']}
                result['openai_flagged'] = False
                
                # Cache the result
                self.cache.cache_result(cache_key, result)
                
                return result
                
            except json.JSONDecodeError:
                # Fallback parsing if JSON is malformed
                result_lower = result_text.lower()
                if 'approved' in result_lower or 'approve' in result_lower:
                    decision = 'approved'
                elif 'rejected' in result_lower or 'reject' in result_lower:
                    decision = 'rejected'
                else:
                    decision = 'rejected'
                
                return {
                    'decision': decision,
                    'reason': result_text[:200],  # Truncate if too long
                    'confidence': 0.7,
                    'moderator_type': 'ai',
                    'categories': {'custom_rule': decision != 'approved'},
                    'category_scores': {'custom_rule': 0.7},
                    'openai_flagged': False
                }
                
        except Exception as e:
            current_app.logger.error(f"Custom prompt analysis error: {str(e)}")
            return {
                'decision': 'rejected',
                'reason': f'Custom analysis error: {str(e)}',
                'confidence': 0.0,
                'moderator_type': 'ai',
                'categories': {'error': True},
                'category_scores': {'error': 1.0},
                'openai_flagged': False
            }

    def _run_baseline_moderation(self, content):
        """Run OpenAI's built-in moderation API for fast baseline safety check"""
        try:
            client = self.client_manager.get_client()
            response = client.moderations.create(input=content)
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
                        attr_name = category.replace('-', '_').replace('/', '_')
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
                    'category_scores': {cat: getattr(category_scores, cat.replace('-', '_').replace('/', '_'), 0) for cat in flagged_categories},
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
                
        except Exception as e:
            current_app.logger.error(f"Baseline moderation error: {str(e)}")
            # If baseline fails, be conservative and reject
            return {
                'decision': 'rejected',
                'reason': f'Baseline moderation failed: {str(e)}',
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
            cache_key = self.cache.generate_cache_key(content, "enhanced_default")
            cached_result = self.cache.get_cached_result(cache_key)
            if cached_result:
                return cached_result
            
            system_message = """You are a comprehensive content safety moderator. Your job is to identify ANY potentially harmful, inappropriate, or unsafe content.

CRITICAL: Be very strict and thorough. Reject content that contains or promotes:
- Sexual content, NSFW material, or requests to generate such content
- Violence, threats, or harmful activities
- Hate speech, harassment, or discriminatory content
- Illegal activities or dangerous instructions
- Self-harm or suicide content
- Spam or malicious content
- Requests to generate inappropriate content (even if phrased indirectly)

IMPORTANT: Pay special attention to:
- Requests to "generate", "create", "make" inappropriate content
- Coded language or euphemisms for inappropriate content
- Content that tries to bypass safety measures

Be conservative - if there's any doubt about safety, REJECT the content.

Respond with ONLY a JSON object in this exact format:
{
    "decision": "approved|rejected",
    "reason": "Brief explanation of your decision",
    "confidence": 0.95
}"""
            
            user_message = f"""Analyze this content for ANY potentially harmful, inappropriate, or unsafe material:

CONTENT: {content}

Be extremely thorough and strict. Look for:
1. Explicit sexual content or requests to generate NSFW material
2. Violence, threats, or harmful instructions
3. Hate speech or discriminatory content
4. Illegal activities or dangerous advice
5. Any requests to generate inappropriate content
6. Attempts to bypass content filters

If you find ANY of these issues, reject the content immediately.

Respond with ONLY a JSON object:
{{
    "decision": "approved|rejected",
    "reason": "Brief explanation of your decision",
    "confidence": 0.95
}}"""
            
            client = self.client_manager.get_client()
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=150,
                temperature=0.0,
                top_p=1.0,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                result = json.loads(result_text)
                
                # Validate required fields
                if 'decision' not in result or result['decision'] not in ['approved', 'rejected']:
                    result['decision'] = 'rejected'  # Default to reject if unclear
                
                if 'confidence' not in result or not isinstance(result['confidence'], (int, float)):
                    result['confidence'] = 0.8
                
                if 'reason' not in result:
                    result['reason'] = 'Enhanced AI safety analysis completed'
                
                # Add metadata
                result['moderator_type'] = 'ai'
                result['categories'] = {'enhanced_safety': result['decision'] != 'approved'}
                result['category_scores'] = {'enhanced_safety': result['confidence']}
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
                
        except Exception as e:
            current_app.logger.error(f"Enhanced default moderation error: {str(e)}")
            # If enhanced moderation fails, be conservative and reject
            return {
                'decision': 'rejected',
                'reason': f'Enhanced moderation failed: {str(e)}',
                'confidence': 0.0,
                'moderator_type': 'ai',
                'categories': {'error': True},
                'category_scores': {'error': 1.0},
                'openai_flagged': False
            }

    def get_moderation_categories_info(self):
        """Return information about moderation categories for custom prompts"""
        return {
            'hate_speech': 'Content that expresses, incites, or promotes hate based on race, gender, ethnicity, religion, nationality, sexual orientation, disability status, or caste.',
            'harassment': 'Content that expresses, incites, or promotes harassing language towards any target.',
            'violence': 'Content that depicts death, violence, or physical injury, or promotes violent acts.',
            'sexual_content': 'Content meant to arouse sexual excitement, such as the description of sexual activity, or that promotes sexual services.',
            'self_harm': 'Content that promotes, encourages, or depicts acts of self-harm, such as suicide, cutting, and eating disorders.',
            'illicit_activities': 'Content that gives advice or instruction on how to commit illicit acts.',
            'spam': 'Unwanted, repetitive content that is sent in bulk.',
            'misinformation': 'False or misleading information that could cause harm.'
        }