"""
Vector similarity search using pgvector in PostgreSQL.
Replaces the Qdrant-based VectorDB class.
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
import numpy as np

class VectorSearch:
    """Vector similarity search backed by pgvector columns on the products table."""
    def __init__(self, db: Session):
        self.db = db
    
    def search_text(self, query_vector, limit=10, filters=None):
        """
        Search products by text embedding cosine similarity.

        Args:
            query_vector: numpy array (384-dim)
            limit: max results
            filters: optional dict like {"platform": "met_museum", "fp_category": "dress"}
        """
        where_parts = ["text_embedding IS NOT NULL"]
        params = {"vec": str(query_vector.tolist()), "limit": limit}

        if filters:
            for key,value in filters.items():
                if value is not None:
                    safe_key = key  # column name from SearchFilters schema
                    where_parts.append(f"{safe_key} = :{safe_key}")
                    params[safe_key] = value

        where_sql = " AND ".join(where_parts)

        rows = self.db.execute(text(f"""
            SELECT id, title, platform, category, primary_image,
                   era, decade, style_tags, colors, material,
                   garment_type, vibe, fit_style, occasion,
                   ai_description, culture, object_date, price,
                   fp_category,
                   1 - (text_embedding <=> :vec) as score
            FROM products
            WHERE {where_sql}
            ORDER BY text_embedding <=> :vec
            LIMIT :limit                                
        """), params).fetchall()

        return [dict(row._mapping) for row in rows]
    
    def search_image(self, query_vector, limit=10):
        """Search products by image embedding cosine similarity."""
        rows = self.db.execute(text("""
            SELECT id, title, platform, category, primary_image,
                   era, decade, style_tags, colors, material,
                   garment_type, vibe, fit_style, occasion,
                   ai_description, culture, object_date, price,
                   1 - (image_embedding <=> :vec) as score
            FROM products
            WHERE image_embedding IS NOT NULL
            ORDER BY image_embedding <=> :vec
            LIMIT :limit
        """), {"vec": str(query_vector.tolist()), "limit": limit}).fetchall()

        return [dict(row._mapping) for row in rows]
    
    def get_embedding(self, product_id, embedding_type='text'):
        """Retrieve a product's embedding as a numpy array."""
        col = 'text_embedding' if embedding_type == 'text' else 'image_embedding'
        row = self.db.execute(text(f"SELECT {col} FROM products WHERE id = :id"), {"id": product_id}).fetchone()
        if row and row[0]:
            return np.array(row[0])
        return None

    def upsert_embedding(self, product_id, text_vec=None, image_vec=None):
        """Write embeddings to product columns."""
        updates = []
        params = {"id": product_id}

        if text_vec is not None:
            updates.append("text_embedding = :text_vec")
            params["text_vec"] = str(text_vec.tolist())
        
        if image_vec is not None:
            updates.append("image_embedding = :image_vec")
            params["image_vec"] = str(image_vec.tolist())
        
        if updates:
            self.db.execute(
                text(f"UPDATE products SET {', '.join(updates)} WHERE id = :id"),
                params
            )
            self.db.commit()