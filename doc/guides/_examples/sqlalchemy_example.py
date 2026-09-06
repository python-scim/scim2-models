import operator
from datetime import datetime
from datetime import timezone
from enum import Enum

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import and_
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy import func
from sqlalchemy import not_
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker

from scim2_models import Attribute
from scim2_models import InvalidPathException
from scim2_models import Meta
from scim2_models import SearchRequest
from scim2_models import User
from scim2_models.filters import STRING_OPERATORS
from scim2_models.filters import AttrPath
from scim2_models.filters import CompareOperator
from scim2_models.filters import FilterVisitor
from scim2_models.filters import LogicalOperator
from scim2_models.filters import coerce_value

from .integrations import MAX_RESULTS


# -- models-start --
class Base(DeclarativeBase):
    pass


class UserRecord(Base):
    """A user, as the application stores it."""

    __tablename__ = "user"

    id: Mapped[str] = mapped_column(primary_key=True)
    user_name: Mapped[str]
    display_name: Mapped[str | None]
    title: Mapped[str | None]
    active: Mapped[bool] = mapped_column(default=True)
    last_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    emails: Mapped[list["EmailRecord"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    groups: Mapped[list["GroupRecord"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class EmailRecord(Base):
    """One entry of the multi-valued ``emails`` attribute."""

    __tablename__ = "email"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"))
    type: Mapped[str | None]
    value: Mapped[str]


class GroupRecord(Base):
    """One entry of the multi-valued ``groups`` attribute."""

    __tablename__ = "user_group"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"))
    value: Mapped[str]
    display: Mapped[str | None]


# -- models-end --


# -- engine-start --
def create_session_factory(url="sqlite://"):
    """Create the engine and the tables, and return a session factory.

    A case-exact attribute compares with ``LIKE``, which SQLite folds on ASCII
    unless this pragma is set. Other engines settle it with the column collation.
    """
    engine = create_engine(url)

    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _case_sensitive_like(dbapi_connection, _record):
            dbapi_connection.execute("PRAGMA case_sensitive_like = ON")

    Base.metadata.create_all(engine)
    return sessionmaker(engine)


# -- engine-end --


# -- mapping-start --
def as_utc(value):
    """Make a stored instant aware, since a SCIM ``dateTime`` carries an offset."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def to_scim_user(record, location=None):
    """Convert a stored user into a SCIM User resource."""
    return User(
        id=record.id,
        user_name=record.user_name,
        display_name=record.display_name,
        title=record.title,
        active=record.active,
        emails=[
            User.Emails(type=email.type, value=email.value) for email in record.emails
        ]
        or None,
        groups=[
            User.Groups(value=group.value, display=group.display)
            for group in record.groups
        ]
        or None,
        meta=Meta(
            resource_type="User",
            last_modified=as_utc(record.last_modified),
            location=location,
        ),
    )


def from_scim_user(scim_user):
    """Convert a validated SCIM payload into stored rows."""
    return UserRecord(
        id=scim_user.id,
        user_name=scim_user.user_name,
        display_name=scim_user.display_name,
        title=scim_user.title,
        active=True if scim_user.active is None else scim_user.active,
        last_modified=datetime.now(timezone.utc),
        emails=[
            EmailRecord(type=str(email.type) if email.type else None, value=email.value)
            for email in scim_user.emails or []
        ],
        groups=[
            GroupRecord(value=group.value, display=group.display)
            for group in scim_user.groups or []
        ],
    )


# -- mapping-end --


# -- columns-start --
COLUMNS = {
    ("id", None): (None, UserRecord.id),
    ("user_name", None): (None, UserRecord.user_name),
    ("display_name", None): (None, UserRecord.display_name),
    ("title", None): (None, UserRecord.title),
    ("active", None): (None, UserRecord.active),
    ("meta", "last_modified"): (None, UserRecord.last_modified),
    ("emails", None): (UserRecord.emails, None),
    ("emails", "type"): (UserRecord.emails, EmailRecord.type),
    ("emails", "value"): (UserRecord.emails, EmailRecord.value),
    ("groups", None): (UserRecord.groups, None),
    ("groups", "value"): (UserRecord.groups, GroupRecord.value),
    ("groups", "display"): (UserRecord.groups, GroupRecord.display),
}
# -- columns-end --


# -- visitor-start --
COMPARISONS = {
    CompareOperator.eq: operator.eq,
    CompareOperator.ne: operator.ne,
    CompareOperator.gt: operator.gt,
    CompareOperator.ge: operator.ge,
    CompareOperator.lt: operator.lt,
    CompareOperator.le: operator.le,
}

STRING_METHODS = {
    CompareOperator.co: ("contains", "icontains"),
    CompareOperator.sw: ("startswith", "istartswith"),
    CompareOperator.ew: ("endswith", "iendswith"),
}


class SqlAlchemyVisitor(FilterVisitor):
    """Turn a parsed filter into a SQLAlchemy expression.

    The expression is meant for the ``WHERE`` clause of a ``select`` over
    :class:`UserRecord`.
    """

    def __init__(self, scim_filter, scope=None):
        self.filter = scim_filter
        self.scope = scope

    def path(self, attr_path):
        """Qualify a path with the attribute a value selection scopes it to."""
        if self.scope is None:
            return attr_path
        return AttrPath(self.scope, attr_path.attr)

    def target(self, resolved):
        """Return the relationship and the column an attribute is stored in."""
        key = (resolved.field_name, resolved.sub_field_name)
        if key not in COLUMNS:
            raise InvalidPathException(path=str(resolved.urn))
        return COLUMNS[key]

    def casefolded(self, resolved):
        """Only a string has a case, and only some strings ignore it."""
        scim_type = Attribute.Type.from_python(resolved.target_type)
        return scim_type == Attribute.Type.string and not resolved.case_exact

    def bind(self, resolved, node):
        """Return the comparison value in the type the column holds."""
        value = coerce_value(resolved, node.value, node.op)
        if isinstance(value, Enum):
            return str(value)
        return value

    def condition(self, resolved, column, op, value):
        """Compare a column, following the case sensitivity of the attribute."""
        folded = self.casefolded(resolved)
        if op in STRING_OPERATORS:
            method = STRING_METHODS[op][folded]
            return getattr(column, method)(value, autoescape=True)

        left, right = column, value
        if folded:
            left, right = func.lower(column), func.lower(value)

        compared = COMPARISONS[op](left, right)
        if op != CompareOperator.ne:
            return compared
        # SQL discards a NULL column, where a missing attribute is not equal.
        return or_(column.is_(None), compared)

    def join(self, relationship_, condition, negated=False):
        """Correlate a condition with the rows of a multi-valued attribute."""
        if relationship_ is None or self.scope is not None:
            return condition
        return (
            not_(relationship_.any(condition))
            if negated
            else relationship_.any(condition)
        )

    def visit_comparison(self, node):
        resolved = self.filter.resolve_comparison(self.path(node.attr_path))
        relationship_, column = self.target(resolved)
        # ``ne`` holds when no value matches, so a multi-valued attribute negates the
        # subquery instead of comparing inside it. A selection scopes it back to one entry.
        negated = (
            node.op == CompareOperator.ne
            and relationship_ is not None
            and self.scope is None
        )
        op = CompareOperator.eq if negated else node.op
        value = self.bind(resolved, node)
        condition = self.condition(resolved, column, op, value)
        return self.join(relationship_, condition, negated=negated)

    def visit_present(self, node):
        resolved = self.filter.resolve(self.path(node.attr_path))
        relationship_, column = self.target(resolved)
        if column is None:
            return relationship_.any()
        return self.join(relationship_, column.is_not(None))

    def visit_not(self, node):
        return not_(self.visit(node.expr))

    def visit_logical_expr(self, node):
        combine = and_ if node.op == LogicalOperator.and_ else or_
        return combine(*(self.visit(term) for term in node.terms))

    def visit_value_path(self, node):
        resolved = self.filter.resolve(node.attr_path)
        relationship_, _column = self.target(resolved)
        scoped = SqlAlchemyVisitor(self.filter, scope=node.attr_path.attr)
        return relationship_.any(scoped.visit(node.val_filter))


# -- visitor-end --


# -- query-start --
def sort_column(sort_by):
    """Return the column a ``sortBy`` parameter names.

    :param sort_by: The ``sortBy`` query parameter.
    :raises InvalidPathException: If the attribute is unknown or not sortable.
    """
    field_name = sort_by.field_name
    relationship_, column = COLUMNS.get((field_name, None), (None, None))
    if column is None or relationship_ is not None:
        raise InvalidPathException(
            path=str(sort_by), detail=f"Cannot sort on {sort_by!r}"
        )
    return column


def query_users(session, search_request):
    """Return the total number of matching users, and the requested page.

    Filtering, sorting and pagination all happen in the database, so
    ``totalResults`` counts what the filter kept without reading the rows.

    :param session: The SQLAlchemy session to query.
    :param search_request: The parsed query parameters.
    :raises InvalidFilterException: If the filter does not apply to the model.
    """
    statement = select(UserRecord)

    if search_request.filter:
        scim_filter = search_request.filter
        statement = statement.where(SqlAlchemyVisitor(scim_filter).visit(scim_filter.ast))

    total = session.scalar(
        select(func.count()).select_from(statement.subquery())
    )

    if search_request.sort_by:
        column = sort_column(search_request.sort_by)
        descending = search_request.sort_order == SearchRequest.SortOrder.descending
        statement = statement.order_by(column.desc() if descending else column)

    start = search_request.start_index_0 or 0
    count = search_request.count or MAX_RESULTS
    statement = statement.offset(start).limit(min(count, MAX_RESULTS))
    return total, session.scalars(statement).all()


# -- query-end --
