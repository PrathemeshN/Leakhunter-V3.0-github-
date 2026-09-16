from elasticsearch import Elasticsearch
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize client
es_client = Elasticsearch(
    settings.ELASTICSEARCH_URL,
    max_retries=3,
    retry_on_timeout=True
)

BREACHES_INDEX = "leakhunter_breaches"


async def init_elasticsearch():
    """
    Initializes Elasticsearch indexes and mappings if they do not exist.
    """
    try:
        if not es_client.ping():
            logger.warning("Could not ping Elasticsearch cluster. Retrying or skipping in offline mode.")
            return False
            
        # Initialize ILM Policy for Production (e.g., rollover after 30 days or 50GB, delete after 90 days)
        ilm_policy_name = "leakhunter_retention_policy"
        try:
            es_client.ilm.put_lifecycle(
                name=ilm_policy_name,
                policy={
                    "policy": {
                        "phases": {
                            "hot": {
                                "actions": {
                                    "rollover": {"max_age": "30d", "max_size": "50gb"}
                                }
                            },
                            "delete": {
                                "min_age": "90d",
                                "actions": {"delete": {}}
                            }
                        }
                    }
                }
            )
            logger.info("Elasticsearch ILM retention policy enforced.")
        except Exception as ilm_e:
            logger.warning(f"Could not enforce ILM policy (requires higher privilege or ELK tier): {ilm_e}")
            
        # Check if index exists
        if not es_client.indices.exists(index=BREACHES_INDEX):
            mappings = {
                "settings": {
                    "index.lifecycle.name": ilm_policy_name,
                    "number_of_shards": 2,
                    "number_of_replicas": 1
                },
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "source_id": {"type": "keyword"},
                        "title": {
                            "type": "text",
                            "fields": {
                                "keyword": {"type": "keyword", "ignore_above": 256}
                            }
                        },
                        "description": {"type": "text"},
                        "breach_date": {"type": "date"},
                        "discovered_date": {"type": "date"},
                        "data_types": {"type": "keyword"},
                        "record_count": {"type": "long"},
                        "severity_score": {"type": "integer"},
                        "original_url": {"type": "keyword"},
                        "affected_domains": {"type": "keyword"},
                        "affected_countries": {"type": "keyword"},
                        "raw_content": {"type": "text"},
                        "status": {"type": "keyword"}
                    }
                }
            }
            es_client.indices.create(index=BREACHES_INDEX, body=mappings)
            logger.info(f"Elasticsearch index '{BREACHES_INDEX}' created successfully.")
        else:
            logger.info(f"Elasticsearch index '{BREACHES_INDEX}' already exists.")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Elasticsearch: {e}")
        return False


async def index_breach(breach_id: str, data: dict):
    """
    Indexes or updates a breach document in Elasticsearch.
    """
    try:
        # Format doc
        doc = {
            "id": str(breach_id),
            "source_id": str(data.get("source_id", "")),
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "breach_date": data.get("breach_date"),
            "discovered_date": data.get("discovered_date"),
            "data_types": data.get("data_types", []),
            "record_count": data.get("record_count", 0),
            "severity_score": data.get("severity_score", 0),
            "original_url": data.get("original_url", ""),
            "affected_domains": data.get("affected_domains", []),
            "affected_countries": data.get("affected_countries", []),
            "raw_content": data.get("raw_content", ""),
            "status": data.get("status", "active")
        }
        res = es_client.index(index=BREACHES_INDEX, id=str(breach_id), body=doc)
        return res
    except Exception as e:
        logger.error(f"Failed to index breach {breach_id} in ES: {e}")
        return None


async def search_breaches(query_string: str, filters: dict = None):
    """
    Performs full-text search on indexed breaches.
    """
    try:
        # Build query
        must_queries = []
        if query_string:
            must_queries.append({
                "multi_match": {
                    "query": query_string,
                    "fields": ["title^2", "description", "raw_content", "affected_domains"]
                }
            })
        else:
            must_queries.append({"match_all": {}})
            
        # Add filters
        filter_queries = []
        if filters:
            if filters.get("data_types"):
                filter_queries.append({"terms": {"data_types": filters["data_types"]}})
            if filters.get("min_severity"):
                filter_queries.append({"range": {"severity_score": {"gte": filters["min_severity"]}}})
            if filters.get("domains"):
                filter_queries.append({"terms": {"affected_domains": filters["domains"]}})
                
        body = {
            "query": {
                "bool": {
                    "must": must_queries,
                    "filter": filter_queries
                }
            },
            "sort": [{"discovered_date": {"order": "desc"}}],
            "size": 50
        }
        
        response = es_client.search(index=BREACHES_INDEX, body=body)
        hits = response["hits"]["hits"]
        return [hit["_source"] for hit in hits]
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []
