from routes.catalog import catalog_bp
from routes.concept_schemes import concept_schemes_bp
from routes.assign import assign_bp
from routes.import_export import import_export_bp
from routes.sync import sync_bp
from routes.mcp import mcp_bp

__all__ = [
    "catalog_bp",
    "concept_schemes_bp",
    "assign_bp",
    "import_export_bp",
    "sync_bp",
    "mcp_bp",
]
