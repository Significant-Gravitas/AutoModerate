import time

import regex as regex_safe  # ReDoS-safe engine with timeout= support
from flask import current_app

# Maximum wall-clock seconds to spend evaluating a single user-supplied regex
# against a single piece of content. Catastrophic-backtrack patterns like
# (a+)+$ will otherwise pin a worker thread indefinitely.
_REGEX_EVAL_TIMEOUT_SECONDS = 1.0


class RuleProcessor:
    """Handles evaluation of different rule types (keyword, regex, AI)"""

    def __init__(self, openai_service):
        self.openai_service = openai_service

    def apply_fast_rule(self, rule, content):
        """Apply keyword/regex rules (instant processing)"""
        start_time = time.time()
        try:
            rule_data = rule.rule_data
            content_text = content.content_data
            matched = False
            reason = ""

            if rule.rule_type == 'keyword':
                matched, reason = self._check_keyword_rule(
                    content_text, rule_data)
            elif rule.rule_type == 'regex':
                matched, reason = self._check_regex_rule(
                    content_text, rule_data)

            if matched:
                return {
                    'decision': rule.action,
                    'confidence': 0.8,
                    'reason': f"Rule '{rule.name}': {reason}",
                    'moderator_type': 'rule',
                    'rule_id': rule.id,
                    'rule_name': rule.name,
                    'rule_type': rule.rule_type,
                    'processing_time': time.time() - start_time,
                    'categories': {f'rule_{rule.rule_type}': True},
                    'category_scores': {f'rule_{rule.rule_type}': 0.8}
                }

            return None

        except Exception as e:
            current_app.logger.error(f"Fast rule error {rule.id}: {str(e)}")
            return None

    def process_ai_rules_batched(self, ai_rules, content):
        """Evaluate all AI-prompt rules against the content in a SINGLE
        OpenAI call.

        The old implementation ran one API call per rule in parallel, which
        made a "Passed all N rules" approval cost N round-trips (~5-10s for
        5 rules on gpt-5-nano). The batched call asks the model to grade every
        rule independently in one response, collapsing that to one round-trip.

        Returns ``{rule_id: rule_match_dict}`` for rules where the content
        VIOLATES the rule — i.e. the rule "matched" and should apply its
        action. Non-matching rules are omitted so the orchestrator can still
        iterate by priority and early-exit on the first match.
        """
        if not ai_rules:
            return {}

        results = {}
        start_time = time.time()

        try:
            by_id = self.openai_service.evaluate_rules_batch(
                content.content_data, ai_rules)
        except Exception as e:
            current_app.logger.error(
                f"Batched AI rule eval raised: {str(e)}", exc_info=True)
            return {}

        total_time = time.time() - start_time

        for rule in ai_rules:
            eval_result = by_id.get(rule.id)
            if not eval_result:
                continue

            # A rejection from evaluate_rules_batch means the content violated
            # the rule — which in rule-processor terms is a "match" that
            # should apply the rule's configured action (typically 'reject').
            if eval_result['decision'] != 'rejected':
                continue

            confidence = eval_result.get('confidence', 0.8)
            reason = eval_result.get('reason', 'AI analysis')

            results[rule.id] = {
                'decision': rule.action,
                'confidence': confidence,
                'reason': f"Rule '{rule.name}': {reason}",
                'moderator_type': 'rule',
                'rule_id': rule.id,
                'rule_name': rule.name,
                'rule_type': rule.rule_type,
                # Every rule in the batch shares the same wall-clock cost
                # because they came from one API call. Recording total_time
                # on each keeps the analytics honest.
                'processing_time': total_time,
                'categories': {'rule_ai_prompt': True},
                'category_scores': {'rule_ai_prompt': confidence},
            }

        # Only log at INFO when something matched — the orchestrator emits a
        # final summary line for every moderation anyway, so logging the
        # zero-match case here is just duplicate noise.
        if results:
            current_app.logger.info(
                f"AI rules (batched): {len(results)}/{len(ai_rules)} matched in {total_time:.2f}s"
            )
        else:
            current_app.logger.debug(
                f"AI rules (batched): 0/{len(ai_rules)} matched in {total_time:.2f}s"
            )
        return results

    def _check_keyword_rule(self, content, rule_data):
        """Check keyword rule matching"""
        keywords = rule_data.get('keywords', [])
        case_sensitive = rule_data.get('case_sensitive', False)

        if not keywords:
            return False, "No keywords defined"

        if isinstance(keywords, str):
            keywords = [line.strip()
                        for line in keywords.split('\n') if line.strip()]

        content_check = content if case_sensitive else content.lower()

        for keyword in keywords:
            keyword_check = keyword if case_sensitive else keyword.lower()
            if keyword_check in content_check:
                return True, f"Matched keyword: '{keyword}'"

        return False, "No keywords matched"

    def _check_regex_rule(self, content, rule_data):
        """Check regex rule matching.

        Uses the third-party ``regex`` library (not stdlib ``re``) so we can
        enforce a wall-clock timeout. Patterns are user-supplied; without a
        timeout, a catastrophic-backtrack pattern is a trivial DoS vector.
        """
        pattern = rule_data.get('pattern', '')
        flags_list = rule_data.get('flags', [])

        if not pattern:
            return False, "No regex pattern defined"

        regex_flags = 0
        if isinstance(flags_list, list):
            for flag in flags_list:
                if flag == 'i':
                    regex_flags |= regex_safe.IGNORECASE
                elif flag == 'm':
                    regex_flags |= regex_safe.MULTILINE
                elif flag == 's':
                    regex_flags |= regex_safe.DOTALL

        try:
            if regex_safe.search(pattern, content, regex_flags, timeout=_REGEX_EVAL_TIMEOUT_SECONDS):
                return True, f"Matched regex: {pattern}"
            return False, "No regex match"
        except TimeoutError:
            current_app.logger.warning(
                f"Regex evaluation timed out after {_REGEX_EVAL_TIMEOUT_SECONDS}s (pattern preview: {pattern[:80]!r})"
            )
            return False, "Regex evaluation timed out (pattern too complex)"
        except regex_safe.error as e:
            return False, f"Invalid regex: {str(e)}"
