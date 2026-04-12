"""SQLAlchemy репозиторий CourseAccessGrant."""

from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, sessionmaker

from src.domain.payments.course_access_grant.entity import CourseAccessGrant
from src.domain.payments.course_access_grant.value_objects import AccessSubject
from src.domain.shared.entity import EntityMeta
from src.domain.shared.statuses import AccessStatus
from src.infrastructure.db.sqlalchemy.models import CourseAccessGrantModel


class SqlAlchemyCourseAccessGrantRepository:
    """Репозиторий доступа к курсам на SQLAlchemy."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get(self, access_grant_id: str) -> CourseAccessGrant | None:
        with self._session_factory() as session:
            model = session.get(CourseAccessGrantModel, access_grant_id)
            return self._to_entity(model) if model else None

    def get_by_payment_intent(self, payment_intent_id: str) -> CourseAccessGrant | None:
        with self._session_factory() as session:
            model = session.scalar(
                select(CourseAccessGrantModel).where(
                    CourseAccessGrantModel.payment_intent_id == payment_intent_id
                )
            )
            return self._to_entity(model) if model else None

    def find_by_course_and_student(
        self,
        course_id: str,
        student_id: str,
    ) -> CourseAccessGrant | None:
        with self._session_factory() as session:
            model = session.scalar(
                select(CourseAccessGrantModel).where(
                    and_(
                        CourseAccessGrantModel.course_id == course_id,
                        CourseAccessGrantModel.student_id == student_id,
                    )
                )
            )
            return self._to_entity(model) if model else None

    def exists_active_by_course_and_student(
        self, course_id: str, student_id: str
    ) -> bool:
        with self._session_factory() as session:
            found = session.scalar(
                select(CourseAccessGrantModel.access_grant_id).where(
                    and_(
                        CourseAccessGrantModel.course_id == course_id,
                        CourseAccessGrantModel.student_id == student_id,
                        CourseAccessGrantModel.status == AccessStatus.ACTIVE.value,
                    )
                )
            )
            return found is not None

    def save(self, access_grant: CourseAccessGrant) -> None:
        with self._session_factory() as session:
            model = session.get(CourseAccessGrantModel, access_grant.access_grant_id)
            if model is None:
                model = CourseAccessGrantModel(
                    access_grant_id=access_grant.access_grant_id
                )
                session.add(model)
            self._fill_model(model, access_grant)
            session.commit()

    @staticmethod
    def _fill_model(model: CourseAccessGrantModel, grant: CourseAccessGrant) -> None:
        model.payment_intent_id = grant.payment_intent_id
        model.course_id = grant.subject.course_id
        model.student_id = grant.subject.student_id
        model.status = grant.status.value
        model.granted_at = grant.granted_at
        model.expires_at = grant.expires_at
        model.revoked_at = grant.revoked_at
        model.revoked_by = grant.revoked_by
        model.revoke_reason = grant.revoke_reason
        model.version = grant.meta.version
        model.created_at = grant.meta.created_at
        model.created_by = grant.meta.created_by
        model.updated_at = grant.meta.updated_at
        model.updated_by = grant.meta.updated_by
        model.archived_at = grant.meta.archived_at
        model.archived_by = grant.meta.archived_by

    @staticmethod
    def _to_entity(model: CourseAccessGrantModel) -> CourseAccessGrant:
        return CourseAccessGrant(
            access_grant_id=model.access_grant_id,
            payment_intent_id=model.payment_intent_id,
            subject=AccessSubject(
                course_id=model.course_id,
                student_id=model.student_id,
            ),
            status=AccessStatus(model.status),
            granted_at=model.granted_at,
            expires_at=model.expires_at,
            revoked_at=model.revoked_at,
            revoked_by=model.revoked_by,
            revoke_reason=model.revoke_reason,
            meta=EntityMeta(
                version=model.version,
                created_at=model.created_at,
                created_by=model.created_by,
                updated_at=model.updated_at,
                updated_by=model.updated_by,
                archived_at=model.archived_at,
                archived_by=model.archived_by,
            ),
            events=[],
        )
