"""RAG service for question answering."""
from typing import List, Dict, Any, Optional
import time
import hashlib
from uuid import UUID

from .embedding_service import EmbeddingService
from .llm_service import LLMService
from .guardrails_service import GuardrailsService
from .cache_service import get_cache_service
from ..db.qdrant import get_qdrant_client
from ..db.repositories.product_repo import ProductRepository
from ..core.config import settings
from ..core.logging import setup_logging
from ..utils.helpers import classify_question_type, QuestionType

logger = setup_logging()


class RAGService:
    """Service for RAG-based question answering."""
    
    SYSTEM_PROMPT = """You are a helpful e-commerce assistant specializing in product recommendations and information.

TONE & STYLE:
- Professional yet friendly and approachable
- Concise and factual - avoid unnecessary fluff
- Use clear formatting (lists, tables, comparisons when helpful)
- No speculation - only use information from the provided context
- Suggest alternatives when relevant and available
- Be helpful and guide users toward good decisions

DOMAIN TERMINOLOGY:
- Use standard e-commerce terms (price, discount, rating, category, etc.)
- Price formatting: Use currency symbols (₹ or $) with proper formatting
- Rating: Format as "X.X/5.0 stars" or "X.X out of 5"
- Categories: Use exact category names from the provided context
- Features: Use technical terms accurately from product descriptions

RESPONSE FORMATS - Few-Shot Examples:

Example 1 - COMPARISON Question:
Question: "Compare these USB cables"
Context: [Product details]
Response Format:
"Here's a comparison of the available USB cables:

**Product A**: [Name]
- Price: ₹X.XX
- Rating: X.X/5.0 stars
- Key Feature: [Feature]
- Best for: [Use case]

**Product B**: [Name]
- Price: ₹X.XX
- Rating: X.X/5.0 stars
- Key Feature: [Feature]
- Best for: [Use case]

Recommendation: [Brief recommendation based on context]"

Example 2 - PRICE Question:
Question: "What are the cheapest options?"
Context: [Product details]
Response Format:
"Here are the most affordable options:

1. **Product Name** - ₹X.XX (Rating: X.X/5.0)
   [Brief value proposition]

2. **Product Name** - ₹X.XX (Rating: X.X/5.0)
   [Brief value proposition]

[Additional context if relevant]"

Example 3 - FEATURE Question:
Question: "Which products support fast charging?"
Context: [Product details]
Response Format:
"Products with fast charging support:

1. **Product Name** (₹X.XX)
   - Fast charging: [Specification]
   - Compatible with: [Devices]
   - Additional features: [List]

2. **Product Name** (₹X.XX)
   - Fast charging: [Specification]
   - [Other relevant details]"

Example 4 - CATEGORY Question:
Question: "What electronics products are available?"
Context: [Product details]
Response Format:
"Available electronics products:

**Category: [Category Name]**
- Product 1 (₹X.XX, X.X/5.0 stars)
- Product 2 (₹X.XX, X.X/5.0 stars)

**Category: [Category Name]**
- Product 3 (₹X.XX, X.X/5.0 stars)

[Brief summary if helpful]"

GENERAL GUIDELINES:
- If context doesn't contain the answer, say: "I don't have information about that in the product catalog. Could you rephrase your question or ask about something else?"
- When comparing, highlight key differences clearly
- When listing products, prioritize by relevance to the question
- Always include price and rating when available
- Keep descriptions concise but informative
"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.llm_service = LLMService()
        self.guardrails = GuardrailsService()
        self.qdrant = get_qdrant_client()
        self.collection_name = settings.qdrant_collection_name
        self.cache = get_cache_service()
    
    async def answer_question(
        self,
        question: str,
        top_k: int = 5,
        product_repo: Optional[ProductRepository] = None
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG.
        
        Args:
            question: User question
            top_k: Number of products to retrieve
            product_repo: Optional product repository for fetching full product data
        
        Returns:
            Dict with answer, retrieved products, and metadata
        """
        start_time = time.time()
        
        # Validate query
        validation = self.guardrails.validate_query(question)
        if not validation["is_valid"]:
            raise ValueError(validation["reason"])
        
        if not validation["is_ecommerce_related"]:
            return {
                "answer": "I can only answer questions about e-commerce products. Please ask about products, prices, categories, or features.",
                "retrieved_products": [],
                "metadata": {"validation": validation},
            }
        
        # Check cache for complete response
        cache_key = self._get_cache_key(question, top_k)
        cached_response = await self.cache.get(cache_key)
        if cached_response:
            logger.info(f"Cache hit for question: {question[:50]}...")
            # Update latency to reflect cache lookup time only
            cache_latency_ms = int((time.time() - start_time) * 1000)
            cached_response["metadata"]["cached"] = True
            cached_response["metadata"]["latency_ms"] = cache_latency_ms
            return cached_response
        
        # Generate query embedding (with caching)
        query_embedding = await self._get_cached_embedding(question)
        
        # Retrieve relevant products from Qdrant
        search_results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
        )
        
        # Extract product IDs and scores
        retrieved_product_ids = []
        retrieval_scores = []
        
        for result in search_results:
            product_id = UUID(result.id)
            retrieved_product_ids.append(product_id)
            retrieval_scores.append(result.score)
        
        # Fetch full product data if repository provided
        # OPTIMIZED: Batch fetch all products in one query instead of sequential queries
        # This reduces connection usage by 5x and latency by 5-10x
        retrieved_products = []
        if product_repo and retrieved_product_ids:
            # Batch fetch all products in one query
            products = await product_repo.get_by_ids(retrieved_product_ids)
            
            # Create a mapping for quick lookup to maintain order
            product_map = {product.id: product for product in products}
            
            # Build product list maintaining the order from retrieval scores
            for product_id in retrieved_product_ids:
                product = product_map.get(product_id)
                if product:
                    retrieved_products.append({
                        "id": str(product.id),
                        "name": product.name,
                        "category": product.category,
                        "price": product.price,
                        "rating": product.rating,
                        "description": product.description,
                    })
        
        # Classify question type
        question_type = classify_question_type(question)
        
        # Build context from retrieved products (enhanced based on question type)
        context = self._build_context(retrieved_products, question_type)
        
        # Get response template hints based on question type
        response_template = self._get_response_template(question_type)
        
        # Generate answer using LLM (optimized prompt)
        prompt = f"""Context:
{context}

Question: {question}

{response_template}

Answer:"""
        
        # Optimized LLM parameters for speed
        answer, llm_stats = await self.llm_service.generate(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.5,  # Lower temperature = faster, more deterministic
            max_tokens=300,    # Reduced from 512 for faster generation
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        result = {
            "answer": answer,
            "retrieved_products": retrieved_products,
            "metadata": {
                "retrieved_count": len(retrieved_products),
                "retrieval_scores": retrieval_scores,
                "latency_ms": latency_ms,
                "validation": validation,
                "question_type": question_type.value,
                "cached": False,
                "llm_stats": llm_stats,  # Pass through LLM statistics for logging
            },
        }
        
        # Cache the response (TTL: 1 hour for common queries)
        await self.cache.set(cache_key, result, ttl=3600)
        
        return result
    
    def _get_cache_key(self, question: str, top_k: int) -> str:
        """Generate cache key for question."""
        # Normalize question (lowercase, strip whitespace)
        normalized = question.lower().strip()
        key_data = f"rag:{normalized}:{top_k}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def _get_cached_embedding(self, text: str) -> List[float]:
        """Get embedding with caching."""
        cache_key = f"embedding:{hashlib.md5(text.encode()).hexdigest()}"
        cached_embedding = await self.cache.get(cache_key)
        
        if cached_embedding:
            logger.debug("Cache hit for embedding")
            return cached_embedding
        
        # Generate embedding
        embedding = self.embedding_service.encode_single(text)
        
        # Cache embedding (TTL: 24 hours - embeddings don't change)
        await self.cache.set(cache_key, embedding, ttl=86400)
        
        return embedding
    
    def _build_context(self, products: List[Dict[str, Any]], question_type: QuestionType = QuestionType.GENERAL) -> str:
        """
        Build context string from retrieved products.
        
        Formats context differently based on question type to provide
        the most relevant information for the LLM.
        """
        if not products:
            return "No products found."
        
        context_parts = []
        
        # For comparison questions, emphasize differences
        if question_type == QuestionType.COMPARISON:
            for i, product in enumerate(products, 1):
                price = product.get('price', 'N/A')
                rating = product.get('rating', 'N/A')
                description = product.get('description', 'N/A')
                
                context_parts.append(
                    f"Product {i}:\n"
                    f"  Name: {product.get('name', 'N/A')}\n"
                    f"  Category: {product.get('category', 'N/A')}\n"
                    f"  Price: ₹{price if price != 'N/A' else 'N/A'}\n"
                    f"  Rating: {rating}/5.0 stars\n"
                    f"  Description: {description[:200] if description != 'N/A' else 'N/A'}\n"  # Reduced from 300
                )
        
        # For price questions, emphasize price and value
        elif question_type == QuestionType.PRICE:
            # Sort by price for price questions
            sorted_products = sorted(
                products,
                key=lambda p: p.get('price', float('inf')) if isinstance(p.get('price'), (int, float)) else float('inf')
            )
            
            for i, product in enumerate(sorted_products, 1):
                price = product.get('price', 'N/A')
                rating = product.get('rating', 'N/A')
                
                context_parts.append(
                    f"Product {i}:\n"
                    f"  Name: {product.get('name', 'N/A')}\n"
                    f"  Price: ₹{price if price != 'N/A' else 'N/A'}\n"
                    f"  Rating: {rating}/5.0 stars\n"
                    f"  Category: {product.get('category', 'N/A')}\n"
                    f"  Description: {product.get('description', 'N/A')[:200]}...\n"
                )
        
        # For feature questions, emphasize description and features
        elif question_type == QuestionType.FEATURE:
            for i, product in enumerate(products, 1):
                description = product.get('description', 'N/A')
                
                context_parts.append(
                    f"Product {i}:\n"
                    f"  Name: {product.get('name', 'N/A')}\n"
                    f"  Category: {product.get('category', 'N/A')}\n"
                    f"  Price: ₹{product.get('price', 'N/A')}\n"
                    f"  Rating: {product.get('rating', 'N/A')}/5.0 stars\n"
                    f"  Description: {description[:250] if description != 'N/A' else 'N/A'}\n"  # Reduced from 400
                )
        
        # For category questions, group by category
        elif question_type == QuestionType.CATEGORY:
            # Group products by category
            by_category = {}
            for product in products:
                category = product.get('category', 'Uncategorized')
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(product)
            
            for category, cat_products in by_category.items():
                context_parts.append(f"\nCategory: {category}")
                for product in cat_products:
                    context_parts.append(
                        f"  - {product.get('name', 'N/A')} "
                        f"(₹{product.get('price', 'N/A')}, "
                        f"{product.get('rating', 'N/A')}/5.0 stars)"
                    )
        
        # Default format for general questions
        else:
            for i, product in enumerate(products, 1):
                price = product.get('price', 'N/A')
                rating = product.get('rating', 'N/A')
                
                context_parts.append(
                    f"Product {i}:\n"
                    f"  Name: {product.get('name', 'N/A')}\n"
                    f"  Category: {product.get('category', 'N/A')}\n"
                    f"  Price: ₹{price if price != 'N/A' else 'N/A'}\n"
                    f"  Rating: {rating}/5.0 stars\n"
                    f"  Description: {product.get('description', 'N/A')[:150]}...\n"  # Reduced from 250
                )
        
        return "\n".join(context_parts)
    
    def _get_response_template(self, question_type: QuestionType) -> str:
        """
        Get response template hints based on question type.
        
        Provides format guidance to the LLM without being too prescriptive.
        """
        templates = {
            QuestionType.COMPARISON: """Format your response as a structured comparison:
- List each product with key attributes
- Highlight key differences clearly
- Provide a brief recommendation if helpful
- Use clear formatting (bullet points, sections)""",
            
            QuestionType.PRICE: """Format your response focusing on price and value:
- List products in price order (cheapest first)
- Include price prominently
- Mention value proposition (rating, features for the price)
- Use clear price formatting""",
            
            QuestionType.FEATURE: """Format your response focusing on features and specifications:
- List products with their relevant features
- Include technical specifications from descriptions
- Highlight compatibility information
- Use clear feature lists""",
            
            QuestionType.CATEGORY: """Format your response by category:
- Group products by their categories
- List products within each category
- Include key details (price, rating) for each
- Use clear category headings""",
            
            QuestionType.GENERAL: """Format your response clearly:
- Use structured formatting (lists, sections)
- Include relevant product details
- Be concise and informative
- Highlight key information"""
        }
        
        return templates.get(question_type, templates[QuestionType.GENERAL])


