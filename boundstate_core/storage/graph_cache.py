"""Graph caching for CAG to avoid rebuilding."""

import pickle
import os
from datetime import datetime, timedelta
from typing import Optional, Any
import logging
import hashlib

logger = logging.getLogger(__name__)

class GraphCache:
    """Cache document graphs to avoid rebuilding."""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
    def get_cache_path(self, index_hash: str) -> str:
        """Get cache file path for index hash."""
        return os.path.join(self.cache_dir, f"graph_{index_hash}.pkl")
    
    def is_cache_valid(self, cache_path: str, max_age_hours: int = 24) -> bool:
        """Check if cache file is still valid."""
        if not os.path.exists(cache_path):
            return False
            
        # Check age
        cache_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        age = datetime.now() - cache_time
        
        return age < timedelta(hours=max_age_hours)
    
    def save_graph(self, graph_builder, cluster_report, index_hash: str):
        """Save graph to cache."""
        cache_path = self.get_cache_path(index_hash)
        
        try:
            cache_data = {
                'graph': graph_builder.graph,
                'nodes': graph_builder.nodes,
                'edges': graph_builder.edges,
                'unmatched_references': getattr(graph_builder, 'unmatched_references', {}),
                'cluster_report': cluster_report,
                'timestamp': datetime.now()
            }
            
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
                
            logger.info(f"[Cache] Saved graph to {cache_path}")
            return True
            
        except Exception as e:
            logger.error(f"[Cache] Failed to save: {e}")
            return False
    
    def load_graph(self, graph_builder, index_hash: str) -> Optional[Any]:
        """Load graph from cache."""
        cache_path = self.get_cache_path(index_hash)
        
        if not self.is_cache_valid(cache_path):
            logger.info("[Cache] Cache miss or expired")
            return None
            
        try:
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)
                
            # Restore graph builder state
            graph_builder.graph = cache_data['graph']
            graph_builder.nodes = cache_data['nodes']
            graph_builder.edges = cache_data['edges']
            if 'unmatched_references' in cache_data:
                graph_builder.unmatched_references = cache_data['unmatched_references']
            
            logger.info(f"[Cache] Loaded graph from {cache_path}")
            return cache_data.get('cluster_report')
            
        except Exception as e:
            logger.error(f"[Cache] Failed to load: {e}")
            return None
    
    def clear_cache(self):
        """Clear all cached graphs."""
        try:
            for file in os.listdir(self.cache_dir):
                if file.startswith('graph_') and file.endswith('.pkl'):
                    os.remove(os.path.join(self.cache_dir, file))
            logger.info("[Cache] Cleared all cached graphs")
        except Exception as e:
            logger.error(f"[Cache] Failed to clear cache: {e}")

def calculate_index_hash(sections: list) -> str:
    """Calculate hash of index for cache key."""
    # Simple hash based on document count and sample IDs
    doc_count = len(sections)
    sample_ids = sorted([s.get('doc_id', '') for s in sections[:10]])
    hash_input = f"{doc_count}_{':'.join(sample_ids)}"
    
    return hashlib.md5(hash_input.encode()).hexdigest()[:8]