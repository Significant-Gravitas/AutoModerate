from app.models.content import Content
from app.models.moderation_rule import ModerationRule
from app.models.moderation_result import ModerationResult
from app.models.api_user import APIUser
from app.services.openai_service import OpenAIService
from app import db
from flask import current_app
import re
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class CachedRule:
    """Simple data class to hold rule information without SQLAlchemy session dependencies"""
    def __init__(self, id, name, rule_type, action, priority, rule_data):
        self.id = id
        self.name = name
        self.rule_type = rule_type
        self.action = action
        self.priority = priority
        self.rule_data = rule_data
    
    def __repr__(self):
        return f"CachedRule(id={self.id}, name='{self.name}', type='{self.rule_type}')"

class ModerationService:
    _openai_service = None
    _rules_cache = {}
    _cache_timestamps = {}
    _cache_ttl = 300  # 5 minutes
    
    def __init__(self):
        if ModerationService._openai_service is None:
            ModerationService._openai_service = OpenAIService()
        self.openai_service = ModerationService._openai_service
    
    def moderate_content(self, content_id, request_start_time=None):
        """Main moderation function with optimized parallel processing"""
        try:
            content = Content.query.get(content_id)
            if not content:
                return {'error': 'Content not found'}
            
            # Get cached rules and separate by type
            all_rules = self._get_cached_rules(content.project_id)
            fast_rules = [r for r in all_rules if r.rule_type in ['keyword', 'regex']]
            ai_rules = [r for r in all_rules if r.rule_type == 'ai_prompt']
            
            current_app.logger.info(f"Processing {len(fast_rules)} fast rules and {len(ai_rules)} AI rules for content {content_id}")
            
            # Process rules and get final decision
            final_decision, results = self._process_rules(content, fast_rules, ai_rules)
            
            # Handle edge cases
            if not results:
                final_decision, results = self._handle_no_matches(all_rules, content)
            
            # Check for manual review flagging
            if self._should_flag_for_manual_review(results, ai_rules):
                final_decision = 'flagged'
                current_app.logger.info(f"Content {content_id} flagged for manual review")
            
            # Ensure valid status
            if final_decision not in ['approved', 'rejected', 'flagged']:
                final_decision = 'rejected'
            
            # Calculate timing
            total_time = time.time() - request_start_time if request_start_time else 0.0
            
            # Save to database and send updates
            self._save_results(content, final_decision, results, total_time)
            self._send_websocket_update_async(content, final_decision, results, total_time)
            
            return {
                'decision': final_decision,
                'results': results,
                'rule_matched': len(results) > 0,
                'total_rules_checked': len(all_rules),
                'content_id': content.id
            }
            
        except Exception as e:
            current_app.logger.error(f"Moderation error: {str(e)}")
            db.session.rollback()
            return {'error': str(e), 'decision': 'rejected', 'results': []}
    
    def _process_rules(self, content, fast_rules, ai_rules):
        """Process both fast and AI rules, returning first match"""
        results = []
        
        # Process fast rules first
        for rule in fast_rules:
            result = self._apply_fast_rule(rule, content)
            if result:
                results.append(result)
                current_app.logger.info(f"Fast rule '{rule.name}' matched - decision: {result['decision']}")
                return result['decision'], results
        
        # Process AI rules in parallel if no fast rule matched
        if ai_rules:
            ai_results = self._process_ai_rules_parallel(ai_rules, content)
            for rule in ai_rules:  # Maintain priority order
                if rule.id in ai_results:
                    result = ai_results[rule.id]
                    results.append(result)
                    current_app.logger.info(f"AI rule '{rule.name}' matched - decision: {result['decision']}")
                    return result['decision'], results
        
        return None, results
    
    def _handle_no_matches(self, all_rules, content):
        """Handle case when no rules matched"""
        if not all_rules:
            # No rules defined - use default AI moderation
            current_app.logger.info("No rules defined, using default AI moderation")
            result = self._apply_default_ai_moderation(content)
            return result['decision'], [result]
        else:
            # Rules exist but none matched - approve by default
            current_app.logger.info("Content passed all rules - approving")
            result = {
                        'decision': 'approved',
                        'confidence': 0.9,
                'reason': f'Passed all {len(all_rules)} project rules',
                        'moderator_type': 'rule',
                        'processing_time': 0.0,
                        'categories': {'rules_passed': True},
                        'category_scores': {'rules_passed': 0.9}
            }
            return 'approved', [result]
    
    def _save_results(self, content, final_decision, results, total_time):
        """Save moderation results to database with bulk operations"""
        content.status = final_decision
        
        # Update API user stats
        if content.api_user_id:
            api_user = APIUser.query.get(content.api_user_id)
            if api_user:
                api_user.update_stats(final_decision)
            
            # Bulk create moderation results
            if results:
                moderation_results = []
                for i, result in enumerate(results):
                    processing_time = total_time if i == 0 and total_time > 0 else result.get('processing_time', 0.0)
                    
                    moderation_result = ModerationResult(
                        content_id=content.id,
                        decision=result['decision'],
                        confidence=result.get('confidence', 0.0),
                        reason=result.get('reason', ''),
                        moderator_type=result.get('moderator_type', 'unknown'),
                        moderator_id=result.get('rule_id'),
                        processing_time=processing_time,
                        details={
                            'categories': result.get('categories', {}),
                            'category_scores': result.get('category_scores', {}),
                            'openai_flagged': result.get('openai_flagged', False),
                            'rule_id': result.get('rule_id'),
                            'rule_name': result.get('rule_name'),
                            'total_request_time': total_time if i == 0 else None
                        }
                    )
                    moderation_results.append(moderation_result)
                
                db.session.bulk_save_objects(moderation_results)
                
                db.session.commit()
            current_app.logger.info(f"Saved results for content {content.id} - decision: {final_decision}")
    
    def _send_websocket_update_async(self, content, decision, results, total_time):
        """Send WebSocket update in background thread"""
        try:
            content_data = {
                'id': content.id,
                'project_id': content.project_id,
                'content_type': content.content_type,
                'content_data': content.content_data,
                'meta_data': content.meta_data,
                'updated_at': content.updated_at.isoformat()
            }
            
            app = current_app._get_current_object()
            threading.Thread(
                target=self._send_websocket_update,
                args=(app, content_data, decision, results, total_time),
                daemon=True
            ).start()
        except Exception as e:
            current_app.logger.error(f"Failed to start WebSocket thread: {str(e)}")
    
    def _send_websocket_update(self, app, content_data, decision, results, total_time):
        """Send WebSocket update with proper Flask context"""
        try:
            with app.app_context():
                from app import socketio
                
                # Get moderator info from first result
                moderator_type = 'unknown'
                moderator_name = 'Unknown'
                rule_name = None
                
                if results:
                    first_result = results[0]
                    moderator_type = first_result.get('moderator_type', 'unknown')
                    if moderator_type == 'rule':
                        moderator_name = 'Rule'
                        rule_name = first_result.get('rule_name', 'Unknown Rule')
                    elif moderator_type == 'ai':
                        moderator_name = 'AI'
                    else:
                        moderator_name = moderator_type.title()
                
                # Build update data
                content_text = content_data['content_data']
                update_data = {
                    'content_id': content_data['id'],
                    'project_id': content_data['project_id'],
                    'status': decision,
                    'content_type': content_data['content_type'],
                    'content_preview': content_text[:100] + '...' if len(content_text) > 100 else content_text,
                    'meta_data': content_data['meta_data'],
                    'results_count': len(results),
                    'processing_time': total_time or 0.0,
                    'moderator_type': moderator_type,
                    'moderator_name': moderator_name,
                    'rule_name': rule_name,
                    'timestamp': content_data['updated_at']
                }
                
                socketio.emit('moderation_update', update_data, room=f'project_{content_data["project_id"]}')
                app.logger.debug(f"WebSocket update sent for content {content_data['id']}")
                
        except Exception as e:
            try:
                app.logger.error(f"WebSocket error: {str(e)}")
            except:
                print(f"WebSocket error: {str(e)}")
    
    def _get_cached_rules(self, project_id):
        """Get rules with 5-minute caching for performance"""
        current_time = time.time()
        
        # Check cache
        if (project_id in self._rules_cache and 
            project_id in self._cache_timestamps and
            current_time - self._cache_timestamps[project_id] < self._cache_ttl):
            
            current_app.logger.debug(f"Using cached rules for project {project_id}")
            return self._rules_cache[project_id]
        
        # Fetch from database
        current_app.logger.debug(f"Fetching rules from database for project {project_id}")
        try:
            db_rules = ModerationRule.query.filter_by(
                project_id=project_id,
                is_active=True
            ).order_by(ModerationRule.priority.desc()).all()
            
            # Convert to cache-safe objects
            cached_rules = [
                CachedRule(r.id, r.name, r.rule_type, r.action, r.priority, r.rule_data or {})
                for r in db_rules
            ]
            
            # Update cache
            self._rules_cache[project_id] = cached_rules
            self._cache_timestamps[project_id] = current_time
            
            return cached_rules
            
        except Exception as e:
            current_app.logger.error(f"Error fetching rules: {str(e)}")
            return []
    
    def _apply_fast_rule(self, rule, content):
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
    
    def _process_ai_rules_parallel(self, ai_rules, content):
        """Process AI rules in true parallel with optimal performance"""
        if not ai_rules:
            return {}
    
        current_app.logger.info(f"Processing {len(ai_rules)} AI rules in PARALLEL")
        results = {}
        app = current_app._get_current_object()
        
        def process_single_ai_rule(rule):
            try:
                with app.app_context():
                    start_time = time.time()
                    rule_data = rule.rule_data
                    
                    # Create OpenAI service for this thread
                    openai_service = OpenAIService()
                    ai_result = openai_service.moderate_content(
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
            
                    if matched:
                        return (rule.id, {
                            'decision': rule.action,
                            'confidence': confidence,
                            'reason': f"Rule '{rule.name}': {reason}",
                            'moderator_type': 'rule',
                            'rule_id': rule.id,
                            'rule_name': rule.name,
                            'rule_type': rule.rule_type,
                            'processing_time': time.time() - start_time,
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
                        current_app.logger.info(f"AI rule {rule_id} MATCHED - stopping early")
            
                        # Cancel remaining futures
                        for f in futures:
                            if f != future and not f.done():
                                f.cancel()
                        break
            
        except Exception as e:
            current_app.logger.error(f"Parallel AI error: {str(e)}")
        
        current_app.logger.info(f"Parallel AI completed: {len(results)}/{len(ai_rules)} matched")
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
    
    def _apply_default_ai_moderation(self, content):
        """Default AI moderation when no rules exist"""
        start_time = time.time()
        try:
            result = self.openai_service.moderate_content(content.content_data, content.content_type)
            result['processing_time'] = time.time() - start_time
            return result
        except Exception as e:
            current_app.logger.error(f"Default AI error: {str(e)}")
            return {
                'decision': 'rejected',
                'confidence': 0.0,
                'reason': f'AI error: {str(e)}',
                'moderator_type': 'ai',
                'processing_time': time.time() - start_time,
                'categories': {'error': True},
                'category_scores': {'error': 1.0},
                'openai_flagged': False
            }
    
    def _should_flag_for_manual_review(self, results, ai_rules):
        """Determine if content needs manual review"""
        if not results:
            return False
        
        primary_result = results[0]
        confidence = primary_result.get('confidence', 0.0)
        decision = primary_result.get('decision', '')
        
        # Very low confidence
        if confidence < 0.3:
            return True
        
        # Moderate confidence rejection
        if decision == 'rejected' and 0.3 <= confidence <= 0.6:
            return True
            
        # Multiple AI rules with conflicting decisions
        if len(ai_rules) > 1:
            ai_results = [r for r in results if r.get('rule_type') == 'ai_prompt']
            if len(ai_results) > 1:
                decisions = [r.get('decision') for r in ai_results]
                if len(set(decisions)) > 1:
                    return True
            
            return False
    
    def get_project_stats(self, project_id):
        """Get moderation statistics for a project"""
        try:
            total = Content.query.filter_by(project_id=project_id).count()
            approved = Content.query.filter_by(project_id=project_id, status='approved').count()
            rejected = Content.query.filter_by(project_id=project_id, status='rejected').count()
            flagged = Content.query.filter_by(project_id=project_id, status='flagged').count()
            pending = Content.query.filter_by(project_id=project_id, status='pending').count()
            
            return {
                'total': total,
                'approved': approved,
                'rejected': rejected,
                'flagged': flagged,
                'pending': pending,
                'approval_rate': (approved / total * 100) if total > 0 else 0
            }
        except Exception as e:
            current_app.logger.error(f"Stats error: {str(e)}")
            return {'total': 0, 'approved': 0, 'rejected': 0, 'flagged': 0, 'pending': 0, 'approval_rate': 0}
