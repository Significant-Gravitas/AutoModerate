import re
import time
from flask import current_app
from concurrent.futures import ThreadPoolExecutor, as_completed

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
                matched, reason = self._check_keyword_rule(content_text, rule_data)
            elif rule.rule_type == 'regex':
                matched, reason = self._check_regex_rule(content_text, rule_data)
            
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
    
    def process_ai_rules_parallel(self, ai_rules, content):
        """Process AI rules in true parallel with optimal performance"""
        if not ai_rules:
            return {}
    
        results = {}
        app = current_app._get_current_object()
        
        # Log start of parallel processing
        current_app.logger.debug(f"Processing {len(ai_rules)} AI rules in parallel")
        
        def process_single_ai_rule(rule):
            try:
                with app.app_context():
                    start_time = time.time()
                    rule_data = rule.rule_data
                    
                    # Use the provided OpenAI service
                    ai_result = self.openai_service.moderate_content(
                        content.content_data,
                        content.content_type, 
                        rule_data.get('prompt', '')
                    )
            
                    # Check if rule matched
                    if 'configuration_error' in ai_result.get('categories', {}):
                        matched = True
                        reason = "OpenAI unavailable - applying rule action"
                        confidence = 0.5
                    else:
                        matched = ai_result['decision'] == 'rejected'
                        reason = ai_result.get('reason', 'AI analysis')
                        confidence = ai_result.get('confidence', 0.8)
            
                    processing_time = time.time() - start_time
                    app.logger.debug(f"AI rule '{rule.name}': {'matched' if matched else 'passed'} ({processing_time:.2f}s)")
                    
                    if matched:
                        return (rule.id, {
                            'decision': rule.action,
                            'confidence': confidence,
                            'reason': f"Rule '{rule.name}': {reason}",
                            'moderator_type': 'rule',
                            'rule_id': rule.id,
                            'rule_name': rule.name,
                            'rule_type': rule.rule_type,
                            'processing_time': processing_time,
                            'categories': {'rule_ai_prompt': True},
                            'category_scores': {'rule_ai_prompt': confidence}
                        })
                    
                    return (rule.id, None)
                    
            except Exception as e:
                app.logger.error(f"AI rule error {rule.id}: {str(e)}")
                return (rule.id, None)
        
        # Execute in parallel
        try:
            with ThreadPoolExecutor(max_workers=min(len(ai_rules), 10)) as executor:
                futures = {executor.submit(process_single_ai_rule, rule): rule for rule in ai_rules}
                
                for future in as_completed(futures, timeout=30):
                    rule_id, result = future.result()
                    if result:
                        results[rule_id] = result
            
                        # Cancel remaining futures
                        for f in futures:
                            if f != future and not f.done():
                                f.cancel()
                        current_app.logger.debug(f"AI rule matched - cancelling remaining {len([f for f in futures if not f.done()])} rules")
                        break
            
        except Exception as e:
            current_app.logger.error(f"Parallel AI error: {str(e)}")
        
        if results:
            current_app.logger.info(f"AI rules: {len(results)}/{len(ai_rules)} matched")
        else:
            current_app.logger.debug(f"AI rules: 0/{len(ai_rules)} matched - all passed")
        return results
    
    def _check_keyword_rule(self, content, rule_data):
        """Check keyword rule matching"""
        keywords = rule_data.get('keywords', [])
        case_sensitive = rule_data.get('case_sensitive', False)
        
        if not keywords:
            return False, "No keywords defined"
        
        if isinstance(keywords, str):
            keywords = [line.strip() for line in keywords.split('\n') if line.strip()]
        
        content_check = content if case_sensitive else content.lower()
        
        for keyword in keywords:
            keyword_check = keyword if case_sensitive else keyword.lower()
            if keyword_check in content_check:
                return True, f"Matched keyword: '{keyword}'"
        
        return False, "No keywords matched"
    
    def _check_regex_rule(self, content, rule_data):
        """Check regex rule matching"""
        pattern = rule_data.get('pattern', '')
        flags_list = rule_data.get('flags', [])
        
        if not pattern:
            return False, "No regex pattern defined"
        
        regex_flags = 0
        if isinstance(flags_list, list):
            for flag in flags_list:
                if flag == 'i':
                    regex_flags |= re.IGNORECASE
                elif flag == 'm':
                    regex_flags |= re.MULTILINE
                elif flag == 's':
                    regex_flags |= re.DOTALL
        
        try:
            if re.search(pattern, content, regex_flags):
                return True, f"Matched regex: {pattern}"
            return False, "No regex match"
        except re.error as e:
            return False, f"Invalid regex: {str(e)}"