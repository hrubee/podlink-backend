import httpx
import asyncio
from typing import Dict, Any, List, Optional
import time
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class PodchaserClient:
    def __init__(self):
        self.base_url = "https://api.podchaser.com/graphql"
        self.auth_url = "https://api.podchaser.com/oauth/token"
        self.access_token = None
        self.token_expiry = 0
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_access_token(self) -> str:
        """Obtain access token using Podchaser's GraphQL mutation."""
        # Check if we have a valid cached token
        if self.access_token and time.time() < self.token_expiry:
            return self.access_token
        
        # Request new access token using GraphQL mutation
        try:
            mutation = """
            mutation {
              requestAccessToken(
                input: {
                  grant_type: CLIENT_CREDENTIALS
                  client_id: "%s"
                  client_secret: "%s"
                }
              ) {
                access_token
                token_type
                expires_in
              }
            }
            """ % (settings.PODCHASER_API_KEY, settings.PODCHASER_API_SECRET)
            
            response = await self.client.post(
                self.base_url,
                json={"query": mutation},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                logger.error(f"GraphQL Errors: {data['errors']}")
                raise Exception(f"Failed to get access token: {data['errors'][0]['message']}")
            
            token_data = data["data"]["requestAccessToken"]
            self.access_token = token_data["access_token"]
            # Set expiry with 5 minute buffer (default is 1 year = 31536000 seconds)
            self.token_expiry = time.time() + token_data.get("expires_in", 31536000) - 300
            
            logger.info("Successfully obtained Podchaser access token")
            return self.access_token
            
        except Exception as e:
            logger.error(f"Failed to obtain access token: {e}")
            raise

    async def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes a GraphQL query with automatic retries and basic rate limit handling."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Get valid access token
                token = await self.get_access_token()
                
                response = await self.client.post(
                    self.base_url,
                    json={"query": query, "variables": variables},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 429:  # Rate limit
                    wait_time = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                if "errors" in data:
                    logger.error(f"GraphQL Errors: {data['errors']}")
                    raise Exception(f"GraphQL Error: {data['errors'][0]['message']}")
                
                return data["data"]
                
            except (httpx.HTTPError, Exception) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed after {max_retries} attempts: {str(e)}")
                    raise
                wait = 2 ** attempt
                logger.info(f"Attempt {attempt + 1} failed. Retrying in {wait}s...")
                await asyncio.sleep(wait)

    async def get_podcast_details(self, podcast_id: str):
        """Get detailed information about a specific podcast."""
        query = """
        query ($identifier: PodcastIdentifier!) {
          podcast(identifier: $identifier) {
            id
            title
            description
            ratingAverage
            categories { title }
            socialLinks { 
              twitter 
              instagram 
              youtube 
              linkedin 
            }
            imageUrl
            webUrl
            rssUrl
            language
          }
        }
        """
        variables = {
            "identifier": {
                "id": podcast_id,
                "type": "PODCHASER"
            }
        }
        return await self.execute_query(query, variables)

    async def search_podcasts(self, search_term: str, first: int = 10, page: int = 1):
        """Search for podcasts by keyword."""
        query = """
        query ($searchTerm: String!, $first: Int, $page: Int) {
          podcasts(searchTerm: $searchTerm, first: $first, page: $page) {
            paginatorInfo {
              currentPage
              lastPage
              total
            }
            data {
              id
              title
              description
              imageUrl
              ratingAverage
              categories { title }
            }
          }
        }
        """
        variables = {
            "searchTerm": search_term,
            "first": first,
            "page": page
        }
        return await self.execute_query(query, variables)

    async def search_creators(self, search_term: str, first: int = 10, page: int = 1):
        """Search for podcast creators (hosts/guests) by name."""
        query = """
        query ($searchTerm: String!, $first: Int, $page: Int) {
          creators(searchTerm: $searchTerm, first: $first, page: $page) {
            paginatorInfo {
              currentPage
              lastPage
              total
            }
            data {
              pcid
              name
              bio
              imageUrl
              subtitleShort
              episodeAppearanceCount
            }
          }
        }
        """
        variables = {
            "searchTerm": search_term,
            "first": first,
            "page": page
        }
        return await self.execute_query(query, variables)

    async def get_creator_details(self, creator_id: str):
        """Get detailed information about a specific creator."""
        query = """
        query ($identifier: CreatorIdentifier!) {
          creator(identifier: $identifier) {
            pcid
            name
            bio
            imageUrl
            location
            socialLinks {
              twitter
              instagram
              youtube
              linkedin
            }
            credits(first: 20) {
              data {
                podcast {
                  id
                  title
                  imageUrl
                }
                role {
                  name
                }
              }
            }
          }
        }
        """
        variables = {
            "identifier": {
                "id": creator_id,
                "type": "PODCHASER"
            }
        }
        return await self.execute_query(query, variables)

    async def get_trending_podcasts(self, first: int = 20):
        """Get trending/popular podcasts."""
        query = """
        query ($first: Int) {
          podcasts(first: $first) {
            data {
              id
              title
              description
              imageUrl
              ratingAverage
              categories { title }
            }
          }
        }
        """
        variables = {"first": first}
        return await self.execute_query(query, variables)

    async def get_podcasts_by_category(self, category_slug: str, first: int = 20):
        """Get podcasts filtered by category."""
        query = """
        query ($filters: PodcastFilters, $first: Int) {
          podcasts(filters: $filters, first: $first) {
            data {
              id
              title
              description
              imageUrl
              ratingAverage
              categories { title }
            }
          }
        }
        """
        variables = {
            "filters": {
                "categoryId": category_slug
            },
            "first": first
        }
        return await self.execute_query(query, variables)
