"""
Claude API integration for product enrichment.
Analyzes products and returns vintage-specific metadata.
"""

import anthropic
import os
import json
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class ClaudeEnricher:
    """Enriches fashion products with Claude AI"""

    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.async_client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    def enrich_product(
        self,
        title: str,
        category: str,
        color: Optional[str] = None,
        season: Optional[str] = None,
        year: Optional[float] = None,
        material: Optional[str] = None,
        pattern: Optional[str] = None,
        culture: Optional[str] = None,
        period: Optional[str] = None,
        era: Optional[str] = None,
        object_date: Optional[str] = None,
        image_data_url: Optional[str] = None
    ) -> Dict:
        """
        Analyze a fashion product and return vintage-specific metadata.
        """

        prompt = self._build_enrichment_prompt(
            title, category, color, season, year, material, pattern,
            culture, period, era, object_date
        )

        content = []

        # Add image if available
        if image_data_url and image_data_url.startswith('data:image'):
            header, encoded = image_data_url.split(',', 1)
            media_type = header.split(':')[1].split(';')[0]

            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": encoded
                }
            })

        content.append({
            "type": "text",
            "text": prompt
        })

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            temperature=0.4,
            system="You are a fashion historian and vintage style expert. Return only valid JSON.",
            messages=[{
                "role": "user",
                "content": content
            }]
        )

        response_text = response.content[0].text

        # Extract JSON from response
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text.strip()

        try:
            enrichment = json.loads(json_str)
            return enrichment
        except json.JSONDecodeError as e:
            print(f"  JSON parse error: {e}")
            print(f"  Response: {response_text[:200]}")
            return self._get_fallback_enrichment(title, category)

    def _build_enrichment_prompt(
        self,
        title: str,
        category: str,
        color: Optional[str],
        season: Optional[str],
        year: Optional[float],
        material: Optional[str] = None,
        pattern: Optional[str] = None,
        culture: Optional[str] = None,
        period: Optional[str] = None,
        era: Optional[str] = None,
        object_date: Optional[str] = None
    ) -> str:

        prompt = f"""Analyze this historical fashion item and provide rich metadata that bridges museum catalog language with how modern people search for fashion inspiration.

**Item Details:**
- Title: {title}
- Category: {category}"""

        if object_date:
            prompt += f"\n- Date (from museum records): {object_date}"
        if era:
            prompt += f"\n- Era: {era}"
        if period:
            prompt += f"\n- Period: {period}"
        if culture:
            prompt += f"\n- Culture: {culture}"
        if material:
            prompt += f"\n- Material: {material}"
        if color:
            prompt += f"\n- Color: {color}"
        if pattern:
            prompt += f"\n- Pattern: {pattern}"
        if season:
            prompt += f"\n- Season: {season}"
        if year:
            prompt += f"\n- Year: {int(year)}"

        prompt += """

**Your Task:**
Analyze this item using the Fashionpedia fashion ontology (27 apparel categories, 294 attributes) combined with vintage/historical expertise. Provide structured metadata that helps modern users find this item.

Return a JSON response with these fields:

=== FASHIONPEDIA STRUCTURED FIELDS (pick from the given options) ===

1. **fp_category**: The closest Fashionpedia main apparel category. Pick ONE:
   shirt/blouse | top/t-shirt/sweatshirt | sweater | cardigan | jacket | vest |
   pants | shorts | skirt | coat | dress | jumpsuit | cape | glasses | hat |
   headband/head covering/hair accessory | tie | glove | watch | belt |
   leg warmer | tights/stockings | sock | shoe | bag/wallet | scarf | umbrella

2. **nickname**: The specific garment sub-type nickname. Pick the best match or null:
   Tops: polo, henley, camisole, tank top, peasant top, tunic, smock, crop top, halter top
   Jackets: blazer, bomber, pea jacket, puffer, biker, trucker, safari, military, bolero, tuxedo, varsity, windbreaker
   Pants: jeans, leggings, culottes, capri, harem, jodhpur, cargo pants, sailor pants
   Skirts: wrap skirt, skater, pencil, prairie, kilt, tulip, dirndl, accordion, sarong, flamenco
   Coats: trench, parka, pea coat, duster, puffer coat, kimono, robe, shearling coat, military coat, wrap coat
   Dresses: wrap dress, slip dress, shift dress, sheath dress, shirt dress, sundress, bodycon, kaftan, tea dress, gown, sweater dress, blouson dress
   Shorts: bermuda, boardshorts, skort, trunks, bloomers

3. **silhouette**: Overall garment shape. Pick ONE or null:
   a-line | pencil | straight | fit and flare | flare | trumpet | mermaid |
   balloon | bell | bell bottom | bootcut | wide leg | peg | tent | baggy |
   circle | peplum | high low | asymmetrical | tight fit | regular fit | loose fit | oversized

4. **neckline**: Neckline type. Pick ONE or null:
   v-neck | crew neck | round neck | boat neck | scoop neck | square neckline |
   sweetheart | plunging | keyhole | halter neck | off-the-shoulder | one shoulder |
   turtle neck | cowl neck | high neck | collarless | surplice | u-neck |
   queen anne | straight across | illusion | crossover | choker | oval neck

5. **waistline**: Waist placement. Pick ONE or null:
   empire waistline | high waist | normal waist | low waist | dropped waistline | basque waistline | no waistline

6. **length**: Garment length. Pick ONE or null:
   above-the-hip | hip length | micro | mini | above-the-knee | knee length |
   below the knee | midi | maxi | floor length

7. **sleeve_length**: Sleeve length. Pick ONE or null:
   sleeveless | short | elbow-length | three quarter | wrist-length

8. **opening_type**: How the garment opens. Pick ONE or null:
   single breasted | double breasted | zip-up | wrapping | lace up | buckled | toggled | no opening

9. **textile_pattern**: Surface pattern. Pick ONE:
   plain | floral | stripe | check | dot | geometric | paisley | abstract |
   camouflage | houndstooth | herringbone | chevron | argyle | fair isle |
   toile de jouy | leopard | snakeskin | zebra | plant | letters/numbers

10. **textile_finishing**: Manufacturing techniques visible. Pick 1-3 as array:
    Options: distressed | quilted | pleated | ruched | cutout | slit | tiered |
    smocking | gathering | frayed | embossed | printed | burnout | perforated | applique | beaded | sequined | rivet
    Example: ["pleated", "beaded"]

11. **garment_parts**: Notable garment parts visible. Pick as array:
    Options: hood | collar | lapel | epaulette | sleeve | pocket | neckline | buckle | zipper
    Example: ["collar", "sleeve", "pocket"]

12. **decorations**: Decorative elements visible. Pick as array or []:
    Options: applique | bead | bow | flower | fringe | ribbon | rivet | ruffle | sequin | tassel
    Example: ["bow", "ribbon"]

=== CREATIVE / SEARCH-BRIDGE FIELDS (be specific and varied) ===

13. **era**: Broad historical era: "Regency", "Victorian", "Edwardian", "Art Deco", "Mid-Century Modern", "Belle Époque", "Rococo", "Baroque", "Georgian", etc.

14. **decade**: Specific decade from museum date: "1780s", "1860s", "1920s", "1955-1960", etc.

15. **style_tags**: Array of 3-5 terms mixing historical AND modern aesthetics. Be specific to the item.
    Historical: "Rococo", "Neoclassical", "Victorian", "Edwardian", "Regency", "Belle Époque", "Aesthetic Movement"
    Modern: "dark academia", "cottagecore", "royalcore", "coquette", "balletcore", "old money",
      "bohemian", "ethereal", "maximalist", "preppy", "grunge", "avant-garde", "witchy", "coastal grandma"

16. **colors**: Array of 2-4 specific colors: ["ivory", "gold thread"], ["dusty rose", "sage green"], etc.

17. **material**: Primary fabric: "silk taffeta", "cotton muslin", "wool broadcloth", "velvet", "lace over silk", "brocade", etc.

18. **season**: "spring/summer", "fall/winter", "all-season", or "evening"

19. **garment_type**: Specific garment type in natural language: "bustle evening gown", "tailored riding jacket", "opera-length gloves", etc.

20. **vibe**: 1-3 word modern aesthetic vibe. Be creative: "dark academia", "quiet luxury", "fairy tale elegance", "moody romantic", etc.

21. **fit_style**: Silhouette description in natural language: "corseted fitted", "flowing draped", "oversized relaxed", etc.

22. **occasion**: "formal evening", "garden party", "everyday wear", "wedding or bridal", "editorial inspiration", etc.

23. **ai_description**: Rich 2-3 sentence description bridging museum language with modern search terms. Use BOTH historical context AND modern aesthetic vocabulary.

**Return ONLY valid JSON, no markdown:**

{
  "fp_category": "...",
  "nickname": "...",
  "silhouette": "...",
  "neckline": null,
  "waistline": "...",
  "length": "...",
  "sleeve_length": "...",
  "opening_type": null,
  "textile_pattern": "...",
  "textile_finishing": ["..."],
  "garment_parts": ["..."],
  "decorations": [],
  "era": "...",
  "decade": "...",
  "style_tags": ["...", "..."],
  "colors": ["...", "..."],
  "material": "...",
  "season": "...",
  "garment_type": "...",
  "vibe": "...",
  "fit_style": "...",
  "occasion": "...",
  "ai_description": "..."
}"""

        return prompt

    def enrich_creative_only(
        self,
        title: str,
        category: str,
        existing_fields: Dict,
        image_data_url: Optional[str] = None
    ) -> Dict:
        """
        For items that already have expert-annotated structured fields (e.g. Fashionpedia),
        only ask Claude for creative/search-bridge fields.
        Returns merged dict: existing structured fields + new creative fields.
        """

        # Build context from existing structured fields
        struct_context = []
        for key in ('fp_category', 'nickname', 'silhouette', 'neckline', 'waistline',
                     'length', 'sleeve_length', 'opening_type', 'textile_pattern'):
            val = existing_fields.get(key)
            if val:
                struct_context.append(f"- {key}: {val}")

        for key in ('textile_finishing', 'garment_parts', 'decorations'):
            val = existing_fields.get(key)
            if val and isinstance(val, list) and val:
                struct_context.append(f"- {key}: {', '.join(val)}")

        prompt = f"""Analyze this fashion item and provide CREATIVE metadata for search discovery.

**Item:** {title}
**Category:** {category}

**Already-annotated structural attributes (expert-labeled, do NOT change these):**
{chr(10).join(struct_context) if struct_context else '(none)'}

Based on the image and attributes above, provide ONLY the creative/search-bridge fields.
Think about: What modern aesthetic does this evoke? What would someone searching for this style type?

Return ONLY valid JSON with these fields:

{{
  "era": "Modern" or a historical era if it evokes one (e.g. "Victorian-inspired"),
  "decade": "2010s" or "2020s" (or null),
  "style_tags": ["3-5 modern aesthetic tags like dark academia, cottagecore, streetwear, minimalist, etc."],
  "colors": ["2-4 specific colors visible in the image"],
  "material": "primary fabric (e.g. cotton, denim, silk, polyester blend)",
  "season": "spring/summer" or "fall/winter" or "all-season",
  "garment_type": "natural language garment description (e.g. fitted blazer, flowy sundress)",
  "vibe": "1-3 word aesthetic vibe (e.g. quiet luxury, street chic, boho romantic)",
  "fit_style": "fit description (e.g. relaxed oversized, body-skimming, structured tailored)",
  "occasion": "best occasion (e.g. everyday casual, date night, office, festival)",
  "ai_description": "Rich 2-3 sentence description using modern search vocabulary. Describe the look, the vibe, and who would wear this."
}}"""

        content = []

        if image_data_url and image_data_url.startswith('data:image'):
            header, encoded = image_data_url.split(',', 1)
            media_type = header.split(':')[1].split(';')[0]
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": encoded
                }
            })

        content.append({"type": "text", "text": prompt})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=800,
            temperature=0.5,
            system="You are a fashion stylist and trend expert. Return only valid JSON.",
            messages=[{"role": "user", "content": content}]
        )

        response_text = response.content[0].text

        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text.strip()

        try:
            creative = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"  JSON parse error: {e}")
            creative = {
                "era": "Modern", "decade": "2010s",
                "style_tags": ["casual", "everyday"],
                "colors": ["unknown"], "material": "unknown",
                "season": "all-season", "garment_type": category,
                "vibe": "casual", "fit_style": "standard",
                "occasion": "everyday",
                "ai_description": f"{title} - modern {category} for everyday wear"
            }

        # Merge: keep existing structured fields, add creative fields
        merged = dict(existing_fields)
        for key in ('era', 'decade', 'style_tags', 'colors', 'material',
                     'season', 'garment_type', 'vibe', 'fit_style',
                     'occasion', 'ai_description'):
            merged[key] = creative.get(key)

        return merged

    def _get_fallback_enrichment(self, title: str, category: str) -> Dict:
        return {
            "fp_category": None,
            "nickname": None,
            "silhouette": None,
            "neckline": None,
            "waistline": None,
            "length": None,
            "sleeve_length": None,
            "opening_type": None,
            "textile_pattern": "plain",
            "textile_finishing": [],
            "garment_parts": [],
            "decorations": [],
            "era": "Modern",
            "decade": None,
            "style_tags": ["casual", "everyday"],
            "colors": ["unknown"],
            "material": "unknown",
            "season": "all-season",
            "garment_type": category.lower(),
            "vibe": "casual comfortable",
            "fit_style": "standard",
            "occasion": "everyday",
            "ai_description": f"{title} - {category} for everyday wear"
        }

    def build_rich_text(self, product_data: Dict, enrichment: Dict) -> str:
        """
        Build natural-language text for embedding.
        Combines Fashionpedia taxonomy terms with creative descriptions.
        Stays under ~256 tokens for all-MiniLM-L6-v2.
        """

        parts = []

        # ai_description first — richest, most search-friendly content
        if enrichment.get('ai_description'):
            parts.append(enrichment['ai_description'])

        # Core identity: what it is, when, where
        garment = enrichment.get('garment_type', '')
        nickname = enrichment.get('nickname', '')
        era = enrichment.get('era', '')
        decade = enrichment.get('decade', '')
        material = enrichment.get('material', '')
        colors = enrichment.get('colors', [])

        identity_bits = []
        if era and decade:
            identity_bits.append(f"{era} era {decade}")
        elif era:
            identity_bits.append(f"{era} era")
        if nickname and nickname != garment:
            identity_bits.append(nickname)
        if garment:
            identity_bits.append(garment)
        if material:
            identity_bits.append(f"in {material}")
        if colors:
            identity_bits.append(", ".join(colors[:3]))
        if identity_bits:
            parts.append(" ".join(identity_bits) + ".")

        # Fashionpedia structural attributes — great for faceted search
        struct_bits = []
        if enrichment.get('silhouette'):
            struct_bits.append(enrichment['silhouette'] + " silhouette")
        if enrichment.get('neckline'):
            struct_bits.append(enrichment['neckline'])
        if enrichment.get('length'):
            struct_bits.append(enrichment['length'])
        if enrichment.get('waistline'):
            struct_bits.append(enrichment['waistline'])
        if enrichment.get('sleeve_length'):
            struct_bits.append(enrichment['sleeve_length'] + " sleeves")
        if struct_bits:
            parts.append(", ".join(struct_bits) + ".")

        # Style and vibe — the modern search bridge
        style_tags = enrichment.get('style_tags', [])
        vibe = enrichment.get('vibe', '')
        if style_tags and vibe:
            parts.append(f"{', '.join(style_tags)}, {vibe}.")
        elif style_tags:
            parts.append(f"{', '.join(style_tags)}.")
        elif vibe:
            parts.append(f"{vibe}.")

        # Textile details and occasion
        extras = []
        if enrichment.get('fit_style'):
            extras.append(enrichment['fit_style'])
        tp = enrichment.get('textile_pattern', '')
        if tp and tp != 'plain':
            extras.append(tp + " pattern")
        finishing = enrichment.get('textile_finishing', [])
        if finishing:
            extras.extend(finishing[:2])
        if enrichment.get('occasion'):
            extras.append(enrichment['occasion'])
        if extras:
            parts.append(f"{', '.join(extras)}.")

        # Decorations — short but searchable
        decos = enrichment.get('decorations', [])
        if decos:
            parts.append(f"Details: {', '.join(decos)}.")

        return " ".join(parts)

    def generate_bridge_narrative(self, item_a, item_b, shared_attributes: dict) -> str:
        """Generate a narrative explaining how two products from different eras are connected based on shared attributes."""
        # Build prompt with source and target product details, emphasizing shared attributes
        prompt = f"""These two fashion items share a style connection:

ITEM A: {item_a['title']}
  Era: {item_a.get('era', 'unknown')} | Material: {item_a.get('material', 'unknown')} | Silhouette: {item_a.get('silhouette', 'unknown')}

ITEM B: {item_b['title']}
  Era: {item_b.get('era', 'unknown')} | Material: {item_b.get('material', 'unknown')} | Silhouette: {item_b.get('silhouette', 'unknown')}

Shared attributes: {shared_attributes}

Explain what connects them. Focus on the shared design DNA and how it transcends time. Be concise, engaging, and insightful."""
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=200,
            temperature=0.6,
            system="You are a fashion historian. Write exactly one or two sentences. No quotes, no preamble. Focus on shared design DNA.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text.strip()

    async def generate_bridge_narrative_async(self, item_a, item_b, shared_attributes: dict) -> str:
        """Async version of generate_bridge_narrative."""
        prompt = f"""These two fashion items share a style connection:

ITEM A: {item_a['title']}
  Era: {item_a.get('era', 'unknown')} | Material: {item_a.get('material', 'unknown')} | Silhouette: {item_a.get('silhouette', 'unknown')}

ITEM B: {item_b['title']}
  Era: {item_b.get('era', 'unknown')} | Material: {item_b.get('material', 'unknown')} | Silhouette: {item_b.get('silhouette', 'unknown')}

Shared attributes: {shared_attributes}

Explain what connects them. Focus on the shared design DNA and how it transcends time. Be concise, engaging, and insightful."""

        response = await self.async_client.messages.create(
            model=self.model,
            max_tokens=200,
            temperature=0.6,
            system="You are a fashion historian. Write exactly one or two sentences. No quotes, no preamble. Focus on shared design DNA.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text.strip()

if __name__ == '__main__':
    print("\nTesting Claude API Integration\n")

    enricher = ClaudeEnricher()

    test_product = {
        'title': 'Turtle Check Men Navy Blue Shirt',
        'category': 'Shirts',
        'color': 'Navy Blue',
        'season': 'Fall',
        'year': 2011.0
    }

    print(f"Test Product:")
    print(f"  {test_product['title']}")
    print(f"  Category: {test_product['category']}")
    print(f"  Color: {test_product['color']}")

    print("\nCalling Claude API...")

    enrichment = enricher.enrich_product(
        title=test_product['title'],
        category=test_product['category'],
        color=test_product['color'],
        season=test_product['season'],
        year=test_product['year']
    )

    print("\nEnrichment Result:")
    print(json.dumps(enrichment, indent=2))

    print("\nRich Text for Embedding:")
    rich_text = enricher.build_rich_text(test_product, enrichment)
    print(f"  {rich_text}")

    print("\nClaude integration working!\n")
