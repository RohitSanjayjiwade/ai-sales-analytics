import json
import logging
from django.apps import apps
from django.core.cache import cache

logger = logging.getLogger(__name__)

EXCLUDED_APPS = {'admin', 'auth', 'contenttypes', 'sessions', 'chat'}

FIELD_TYPE_MAP = {
    'AutoField': 'INTEGER (primary key)',
    'BigAutoField': 'BIGINT (primary key)',
    'CharField': 'VARCHAR',
    'TextField': 'TEXT',
    'EmailField': 'VARCHAR (email)',
    'IntegerField': 'INTEGER',
    'BigIntegerField': 'BIGINT',
    'PositiveIntegerField': 'INTEGER (positive)',
    'FloatField': 'FLOAT',
    'DecimalField': 'DECIMAL',
    'BooleanField': 'BOOLEAN',
    'DateField': 'DATE',
    'DateTimeField': 'DATETIME',
    'ForeignKey': 'INTEGER (foreign key)',
    'UUIDField': 'UUID',
}

SKIP_FIELD_TYPES = {'ManyToManyField', 'ManyToManyRel', 'ManyToOneRel', 'OneToOneRel'}


class SchemaExtractor:
    CACHE_KEY = 'ai_db_schema_v1'
    CACHE_TTL = 3600  # 1 hour

    def get_schema(self):
        """Return cached schema string or build fresh one."""
        cached = cache.get(self.CACHE_KEY)
        if cached:
            logger.debug("SCHEMA — loaded from cache")
            return cached
        logger.info("SCHEMA — cache miss, building from Django models...")
        schema = self._build_schema()
        cache.set(self.CACHE_KEY, schema, self.CACHE_TTL)
        logger.info("SCHEMA — built and cached for %ds", self.CACHE_TTL)
        return schema

    def invalidate(self):
        cache.delete(self.CACHE_KEY)

    def _build_schema(self):
        parts = []
        for model in apps.get_models():
            if model._meta.app_label in EXCLUDED_APPS:
                continue
            parts.append(self._describe_model(model))
        return "\n\n".join(parts)

    def _describe_model(self, model):
        meta = model._meta
        lines = ["Table: {}".format(meta.db_table)]

        doc = (model.__doc__ or '').strip()
        if doc and 'Model' not in doc:
            lines.append("Description: {}".format(doc))

        lines.append("Columns:")
        for field in meta.get_fields():
            desc = self._describe_field(field)
            if desc:
                lines.append("  - {}".format(desc))

        return "\n".join(lines)

    def _describe_field(self, field):
        field_type = type(field).__name__

        if field_type in SKIP_FIELD_TYPES:
            return None

        col_name = getattr(field, 'column', getattr(field, 'name', None))
        if not col_name:
            return None

        sql_type = FIELD_TYPE_MAP.get(field_type, field_type.upper())

        extras = []
        if getattr(field, 'null', False):
            extras.append('nullable')
        if getattr(field, 'unique', False):
            extras.append('unique')

        if field_type == 'ForeignKey':
            related_table = field.related_model._meta.db_table
            extras.append('references {}(id)'.format(related_table))

        choices = getattr(field, 'choices', None)
        if choices:
            choice_map = {str(k): str(v) for k, v in choices}
            extras.append('choices: {}'.format(json.dumps(choice_map)))

        extra_str = ' [{}]'.format(', '.join(extras)) if extras else ''
        return '{} ({}){}'.format(col_name, sql_type, extra_str)
