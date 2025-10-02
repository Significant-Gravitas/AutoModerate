import time

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.models.moderation_result import ModerationResult

from .ai.ai_moderator import AIModerator
from .database_service import db_service
from .error_tracker import error_tracker
from .moderation.rule_cache import RuleCache
from .moderation.rule_processor import RuleProcessor
from .moderation.websocket_notifier import WebSocketNotifier


class ModerationOrchestrator:
    """Main coordinator for content moderation workflow"""

    def __init__(self):
        self.rule_cache = RuleCache()
        self.ai_moderator = AIModerator()
        self.rule_processor = RuleProcessor(self.ai_moderator)
        self.websocket_notifier = WebSocketNotifier()

    async def moderate_content(self, content_id, request_start_time=None):
        """Main moderation function with optimized parallel processing"""
        try:
            content = await db_service.get_content_by_id(content_id)
            if not content:
                return {'error': 'Content not found'}

            # Get cached rules and separate by type
            all_rules = await self.rule_cache.get_cached_rules(content.project_id)
            fast_rules = [
                r for r in all_rules if r.rule_type in ['keyword', 'regex']]
            ai_rules = [r for r in all_rules if r.rule_type == 'ai_prompt']

            # Count tokens once and cache for processing decisions
            content_tokens = self.ai_moderator.count_tokens(
                content.content_data)

            # Store token count temporarily for processing optimization
            content._temp_token_count = content_tokens

            # Process rules and get final decision
            final_decision, results = self._process_rules(
                content, fast_rules, ai_rules)

            # Handle edge cases
            if not results:
                final_decision, results = self._handle_no_matches(
                    all_rules, content)

            # Check for manual review flagging
            if self._should_flag_for_manual_review(results, ai_rules):
                final_decision = 'flagged'
                current_app.logger.info(
                    f"Content {content_id} flagged for manual review")

            # Ensure valid status
            if final_decision not in ['approved', 'rejected', 'flagged']:
                final_decision = 'rejected'

            # Calculate timing
            total_time = time.time() - request_start_time if request_start_time else 0.0

            # Save to database and send updates
            await self._save_results(content, final_decision, results, total_time)
            self.websocket_notifier.send_update_async(
                content, final_decision, results, total_time)

            # Log final result summary with cache info
            if results and results[0].get('rule_name'):
                rule_info = f" ({results[0]['rule_name']})"
            else:
                rule_info = ""

            # Get cache summary for this request
            cache_summary = self.ai_moderator.cache.get_request_cache_summary()
            if cache_summary['stores'] > 0:
                cache_info = f" [Cached {cache_summary['stores']} results, total: {cache_summary['total']}]"
            elif total_time < 1.0:
                cache_info = " [Cache hit]"
            else:
                cache_info = ""

            current_app.logger.info(
                f"Content {content_id}: {final_decision}{rule_info} in {total_time:.2f}s{cache_info}")

            return {
                'decision': final_decision,
                'results': results,
                'rule_matched': len(results) > 0,
                'total_rules_checked': len(all_rules),
                'content_id': content.id
            }

        except SQLAlchemyError as e:
            error_msg = f"Database error during moderation of content {content_id}: {str(e)}"
            current_app.logger.error(error_msg, exc_info=True)
            error_tracker.track_error('database', str(e), content_id=content_id)
            await db_service.rollback_transaction()

            # Save error result to database
            await self._save_error_result(content_id, 'database', str(e))

            return {
                'error': f'Database error: {str(e)}',
                'decision': 'error',
                'results': [{
                    'decision': 'error',
                    'confidence': 0.0,
                    'reason': f'Database error: {str(e)}',
                    'moderator_type': 'system',
                    'processing_time': 0.0
                }],
                'content_id': content_id
            }
        except (ValueError, TypeError, AttributeError) as e:
            error_msg = f"Data processing error during moderation of content {content_id}: {str(e)}"
            current_app.logger.error(error_msg, exc_info=True)
            error_tracker.track_error('processing', str(e), content_id=content_id)
            await db_service.rollback_transaction()

            # Save error result to database
            await self._save_error_result(content_id, 'processing', str(e))

            return {
                'error': f'Processing error: {str(e)}',
                'decision': 'error',
                'results': [{
                    'decision': 'error',
                    'confidence': 0.0,
                    'reason': f'Processing error: {str(e)}',
                    'moderator_type': 'system',
                    'processing_time': 0.0
                }],
                'content_id': content_id
            }
        except Exception as e:
            # Catch-all for unexpected errors
            error_msg = f"Unexpected error during moderation of content {content_id}: {str(e)}"
            current_app.logger.error(error_msg, exc_info=True)
            error_tracker.track_error('moderation', str(e), content_id=content_id)
            await db_service.rollback_transaction()

            # Save error result to database
            await self._save_error_result(content_id, 'unexpected', str(e))

            return {
                'error': f'Unexpected error: {str(e)}',
                'decision': 'error',
                'results': [{
                    'decision': 'error',
                    'confidence': 0.0,
                    'reason': f'Unexpected error: {str(e)}',
                    'moderator_type': 'system',
                    'processing_time': 0.0
                }],
                'content_id': content_id
            }

    def _process_rules(self, content, fast_rules, ai_rules):
        """Process both fast and AI rules, returning first match"""
        results = []

        # Process fast rules first - batch processing for better performance
        for rule in fast_rules:
            result = self.rule_processor.apply_fast_rule(rule, content)
            if result:
                results.append(result)
                return result['decision'], results

        # Process AI rules in parallel if no fast rule matched
        if ai_rules:
            ai_results = self.rule_processor.process_ai_rules_parallel(
                ai_rules, content)
            for rule in ai_rules:  # Maintain priority order
                if rule.id in ai_results:
                    result = ai_results[rule.id]
                    results.append(result)
                    return result['decision'], results

        return None, results

    def _handle_no_matches(self, all_rules, content):
        """Handle case when no rules matched"""
        if not all_rules:
            # No rules defined - use default AI moderation
            current_app.logger.info(
                "No rules defined, using default AI moderation")
            result = self._apply_default_ai_moderation(content)
            return result['decision'], [result]
        else:
            # Rules exist but none matched - approve by default
            # Content passed all rules
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

    def _apply_default_ai_moderation(self, content):
        """Default AI moderation when no rules exist"""
        start_time = time.time()
        try:
            result = self.ai_moderator.moderate_content(
                content.content_data, content.content_type)
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
            ai_results = [r for r in results if r.get(
                'rule_type') == 'ai_prompt']
            if len(ai_results) > 1:
                decisions = [r.get('decision') for r in ai_results]
                if len(set(decisions)) > 1:
                    return True

        return False

    async def _save_results(self, content, final_decision, results, total_time):
        """Save moderation results to database with bulk operations"""
        # Update content status using database service to ensure persistence
        await db_service.update_content_status(content.id, status=final_decision)

        # Update API user stats efficiently
        if content.api_user_id:
            try:
                api_user = await db_service.get_api_user_by_id(content.api_user_id)
                if api_user:
                    api_user.update_stats(final_decision)
            except Exception as e:
                current_app.logger.error(
                    f"Error updating API user stats: {str(e)}")

        # Bulk create moderation results
        if results:
            moderation_results = []
            for i, result in enumerate(results):
                # Use the actual rule processing time, not the total request time
                rule_processing_time = result.get('processing_time', 0.0)

                moderation_result = ModerationResult(
                    content_id=content.id,
                    decision=result['decision'],
                    confidence=result.get('confidence', 0.0),
                    reason=result.get('reason', ''),
                    moderator_type=result.get('moderator_type', 'unknown'),
                    moderator_id=result.get('rule_id'),
                    processing_time=rule_processing_time,  # Actual rule processing time
                    details={
                        'categories': result.get('categories', {}),
                        'category_scores': result.get('category_scores', {}),
                        'openai_flagged': result.get('openai_flagged', False),
                        'rule_id': result.get('rule_id'),
                        'rule_name': result.get('rule_name'),
                        'total_request_time': total_time,  # Store total time in details
                        'rule_processing_time': rule_processing_time  # Store both for clarity
                    }
                )
                moderation_results.append(moderation_result)

            try:
                await db_service.bulk_save_objects(moderation_results)
            except Exception as e:
                current_app.logger.error(
                    f"Error saving moderation results: {str(e)}")
                await db_service.rollback_transaction()
                raise

        try:
            await db_service.commit_transaction()
        except Exception as e:
            current_app.logger.error(
                f"Error committing database changes: {str(e)}")
            await db_service.rollback_transaction()
            raise

    async def get_project_stats(self, project_id):
        """Get moderation statistics for a project"""
        try:
            counts = await db_service.get_content_counts_by_status(project_id)
            total = counts['total']
            approved = counts['approved']

            return {
                'total': total,
                'approved': approved,
                'rejected': counts['rejected'],
                'flagged': counts['flagged'],
                'pending': counts['pending'],
                'approval_rate': (approved / total * 100) if total > 0 else 0
            }
        except Exception as e:
            current_app.logger.error(f"Stats error: {str(e)}")
            return {'total': 0, 'approved': 0, 'rejected': 0, 'flagged': 0, 'pending': 0, 'approval_rate': 0}

    def invalidate_caches(self, project_id=None):
        """Invalidate all caches for a project or globally"""
        self.rule_cache.invalidate_cache(project_id)
        self.ai_moderator.cache.invalidate_cache()
        current_app.logger.info(
            f"Caches invalidated for project: {project_id or 'all'}")

    async def _save_error_result(self, content_id, error_type, error_message):
        """Save error result to database so we can track failures"""
        try:
            # Update content status to 'error'
            await db_service.update_content_status(content_id, status='error')

            # Create error moderation result
            error_result = ModerationResult(
                content_id=content_id,
                decision='error',
                confidence=0.0,
                reason=f'{error_type.title()} error: {error_message}',
                moderator_type='system',
                moderator_id=None,
                processing_time=0.0,
                details={
                    'error_type': error_type,
                    'error_message': error_message,
                    'is_error': True
                }
            )

            await db_service.bulk_save_objects([error_result])
            await db_service.commit_transaction()
            current_app.logger.info(f"Saved error result for content {content_id}")
        except Exception as e:
            current_app.logger.error(f"Failed to save error result for content {content_id}: {str(e)}")
            # Don't raise - we don't want to fail the error handler itself

    def get_system_stats(self):
        """Get comprehensive system statistics"""
        return {
            'rule_cache': self.rule_cache.get_cache_stats(),
            'result_cache': self.ai_moderator.cache.get_cache_stats(),
            'openai_configured': self.ai_moderator.client_manager.is_configured()
        }
