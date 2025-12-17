from flask import Blueprint, request, current_app
from sqlalchemy import create_engine, text

from config import get_database_url

search_bp = Blueprint('search', __name__)


@search_bp.get('/similar')
def similar_get():
    """Get concepts similar to a given question or text using vector similarity search."""
    workspace_client = current_app.workspace_client
    
    query_text = request.args.get('text', '')
    if not query_text:
        return {'error': 'Text is required'}, 400

    limit = request.args.get('limit', 10, type=int)

    # Generate embedding for the query text using Databricks serving endpoint
    response = workspace_client.serving_endpoints.query(
        name="databricks-gte-large-en",
        input=query_text
    )
    embedding = response.data[0].embedding

    # Query the embeddings table using vector similarity search
    engine = create_engine(get_database_url())
    if engine.dialect.name != 'postgresql':
        return {'error': 'Unsupported database engine'}, 500

    query = text("""
        SELECT subject, predicate, object, object_embedding <-> (:embedding)::vector AS similarity
        FROM public.embeddings
        ORDER BY similarity DESC
        LIMIT :limit
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"embedding": str(embedding), "limit": limit})
        rows = [row._asdict() for row in result]

    return {"results": rows, "query": query_text}
