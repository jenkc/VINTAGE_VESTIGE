"""
Claude API integration for product enrichment.
Analyzes products and returns vintage-specific metadata.
"""

import anthropic
import os
import json
from typing import Dict, Optional
from dotenv import load_dotenv
from enrichment.era_taxonomy import normalize_era, build_era_prompt_section

load_dotenv()

VIBE_AXES = """
AESTHETIC AXES — Place this garment on each spectrum.

Each axis is a spectrum between two opposing aesthetic arguments.
For each axis: does this garment argue for pole A or pole B?
If neither pole applies, skip the axis (null).

AXIS 1 — VOLUME
  Exaggerated Volume: structural mass exceeds functional necessity; the outline is the
    subject. Panniers, crinolines, puff sleeves, Comme des Garçons padding.
  Column Minimalism: unbroken vertical line, body-skimming, no structural intervention.
    Fortuny, 1960s shift, The Row.

AXIS 2 — ORNAMENT
  Maximalist Ornament: surface decoration is the primary aesthetic event; excess is meaning.
    Rococo embroidery, Valentino couture, Victorian beading.
  Bare Surface: deliberate absence of decoration; the material itself is the statement.
    Quaker dress, Japanese minimalism, Jil Sander, unadorned linen.

AXIS 3 — EXPOSURE
  Body Display: stages the body for viewing; makes it the subject of attention.
    Court dress décolletage, 1950s swimwear, contemporary bodycon.
  Body Concealment: deliberately obscures the body's form; refuses the gaze.
    Certain religious dress, 1980s power suiting, modest fashion, Balenciaga volume.

AXIS 4 — GENDER
  Gender Conforming: reinforces the gender expectations of its era. A corseted ballgown in
    1860, a grey flannel suit on a man in 1955 — both conform to their moment's codes.
  Gender Defiant: challenges or violates the gender norms of its moment. Bloomers in 1851,
    Marlene Dietrich's tuxedo, men's skirts, androgynous fashion that refuses binary coding.

AXIS 5 — REGISTER
  Transgressive Subversion: deliberately violates sartorial norms; dress as protest.
    Bloomers, punk, early queer fashion, certain streetwear.
  Elite Distinction: communicates social position through understatement and insider codes.
    Savile Row tailoring, old money aesthetics, quiet luxury.

AXIS 6 — OCCASION
  Pastoral Naturalism: invokes nature, rural life, or pre-industrial simplicity.
    18th century pastoral, Arts and Crafts dress, 1970s folk revival, cottagecore.
  Ceremonial Formalism: marks ritual occasion, separates it from the everyday.
    Court dress, ecclesiastical vestment, wedding dress across cultures.

Return as JSON:
"vibe_axes": {
  "volume":    ["Exaggerated Volume" or "Column Minimalism", confidence] or null,
  "ornament":  ["Maximalist Ornament" or "Bare Surface", confidence] or null,
  "exposure":  ["Body Display" or "Body Concealment", confidence] or null,
  "gender":    ["Gender Conforming" or "Gender Defiant", confidence] or null,
  "register":  ["Transgressive Subversion" or "Elite Distinction", confidence] or null,
  "occasion":  ["Pastoral Naturalism" or "Ceremonial Formalism", confidence] or null
}

Rules:
- Only score axes where the garment makes a clear argument for one pole
- Skip (null) axes that don't apply — a plain work shirt may have no occasion argument
- Confidence = how strongly the garment argues for that pole (0.5 = mild, 1.0 = definitive)
- Most garments score on 2-4 axes, not all 6
"""


class ClaudeEnricher:
    """Enriches fashion products with Claude AI"""

    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.async_client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=5)
        self.model = "claude-sonnet-4-20250514"

    def _build_image_content(self, image_data_url: Optional[str]) -> list:
        """Build Claude API image content block from base64 URL or HTTP URL."""
        if not image_data_url:
            return []

        if image_data_url.startswith('data:image'):
            header, encoded = image_data_url.split(',', 1)
            media_type = header.split(':')[1].split(';')[0]
            return [{
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": encoded,
                }
            }]
        elif image_data_url.startswith('http'):
            return [{
                "type": "image",
                "source": {
                    "type": "url",
                    "url": image_data_url,
                }
            }]
        
        return []

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

        content = self._build_image_content(image_data_url)

        content.append({
            "type": "text",
            "text": prompt
        })

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1200,
            temperature=0.4,
            system=self._build_enrichment_system_prompt(),
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
            if 'era' in enrichment:
                enrichment['era'] = normalize_era(enrichment.get('era'))
            return enrichment
        except json.JSONDecodeError as e:
            print(f"  JSON parse error: {e}")
            print(f"  Response: {response_text[:200]}")
            return self._get_fallback_enrichment(title, category)

    def _build_enrichment_system_prompt(self) -> list:
        """Build the static system prompt for enrichment (cacheable)."""
        era_prompt = build_era_prompt_section()

        static_instructions = f"""You are enriching a historical fashion record for Vintage Vestige, a knowledge graph that connects museum archival pieces to modern fashion. You are a fashion historian and vintage style expert. Return only valid JSON, no markdown.

If an image is provided, it is your primary source. Describe what you actually see — not what the metadata claims. If the image contradicts the title, material, or category, trust the image.

For accessories, fashion plates, textiles, or non-garment objects: skip all structural fields (silhouette through decorations) — use null. Focus on material, construction, and cultural context.

For non-Western garments (sari, kimono, hanbok, kaftan, dashiki, cheongsam, huipil, etc.), use the garment's own name in "garment_type" and "nickname". Use null for structural fields (neckline, waistline, etc.) that don't apply to the garment's construction. Pick the closest fp_category or use "dress" / "coat" as rough approximation.

Return a JSON object with ALL fields below. Pick from the given options or null if not applicable.

=== STRUCTURAL FIELDS ===

"fp_category": shirt/blouse | top/t-shirt/sweatshirt | sweater | cardigan | jacket | vest | pants | shorts | skirt | coat | dress | jumpsuit | cape | glasses | hat | headband/head covering/hair accessory | tie | glove | watch | belt | leg warmer | tights/stockings | sock | shoe | bag/wallet | scarf | umbrella
"nickname": Sub-type or garment name (e.g. blazer, trench, slip dress, pencil skirt, sari, kimono, dashiki, kaftan, cheongsam, hanbok) or null
"silhouette": a-line | pencil | straight | fit and flare | flare | trumpet | mermaid | balloon | bell | wide leg | peg | tent | tight fit | regular fit | loose fit | oversized | null
"neckline": v-neck | crew neck | round neck | boat neck | scoop neck | square neckline | sweetheart | plunging | halter neck | off-the-shoulder | one shoulder | turtle neck | cowl neck | high neck | collarless | surplice | null
"waistline": empire waistline | high waist | normal waist | low waist | dropped waistline | no waistline | null
"length": above-the-hip | hip length | mini | above-the-knee | knee length | below the knee | midi | maxi | floor length | null
"sleeve_length": sleeveless | short | elbow-length | three quarter | wrist-length | null
"opening_type": single breasted | double breasted | zip-up | wrapping | lace up | no opening | null
"textile_pattern": plain | floral | stripe | check | dot | geometric | paisley | abstract | houndstooth | herringbone | leopard | toile de jouy
"textile_finishing": Array of 1-3: distressed | quilted | pleated | ruched | cutout | slit | tiered | smocking | gathering | beaded | sequined | applique
"garment_parts": Array: hood | collar | lapel | epaulette | sleeve | pocket | buckle | zipper
"decorations": Array: applique | bead | bow | flower | fringe | ribbon | rivet | ruffle | sequin | tassel

=== CREATIVE FIELDS ===

"era": EXACT name from this list. IMPORTANT: era means WHEN THE ITEM WAS MADE, not what style it evokes. A 2020 dress inspired by Victorian aesthetics is NOT Victorian — it belongs to the era of its manufacture (e.g. Quiet Luxury, Normcore). Use the Date from museum records if provided. Only use visual/stylistic cues for era if no date is available.
{era_prompt}
"decade": The decade the item was made (e.g. "1780s", "1920s", "2010s"). Must match the era — if the Date says 2018, decade is "2010s". Null only if truly unknown.
"style_tags": 3-5 tags mixing historical and modern aesthetics (e.g. "flapper", "Rococo", "cottagecore", "formal", "everyday", "ceremonial", "workwear", "sportswear", "eveningwear")
"colors": 2-4 specific colors visible | inferred from description (e.g. "navy blue", "cream", "burgundy") | "multi-colored"
"material": Primary fabric — refine if provided in input (e.g. "silk" → "silk taffeta"), or determine from image. (e.g. "silk taffeta", "wool broadcloth")
"season": spring/summer | fall/winter | all-season | evening
"garment_type": Natural language (e.g. "bustle evening gown", "tailored riding jacket")
{VIBE_AXES}

"fit_style": Fit description (e.g. "corseted fitted", "flowing draped")
"occasion": e.g. "formal evening", "everyday wear", "garden party"
"ai_description": 80-120 words. Describe what you see: silhouette, construction, materials, surface treatment, and how the garment relates to its era and culture. Be specific about physical details — the width of a lapel, the weight of a fabric, the geometry of a cut. Do NOT use the axis pole names (e.g. do not write "Exaggerated Volume" or "Bare Surface"). Do NOT use generic praise ("stunning", "elegant", "beautiful"). Write for someone who cannot see the garment.

=== CROSS-CULTURAL BRIDGE FIELDS ===

"construction_technique": Array of 1-3 techniques: hand-embroidery | machine-embroidery | hand-weaving | machine-weaving | knitting | crocheting | felting | draping | tailoring | resist-dyeing | block-printing | screen-printing | digital-printing | batik | tie-dye | quilting | smocking | pleating | lacework | beadwork | applique | tapestry | brocade-weaving | jacquard-weaving | hand-sewing | couture-construction | leather-working | metalwork | null
"social_function": Array of 1-2 social roles this garment serves. Prefer terms from this list: wedding | mourning | religious-ceremonial | court-formal | military-uniform | status-signaling | everyday-practical | workwear | sportswear | performance-costume | coming-of-age | festival-celebration | diplomatic-gift | academic-formal | protest-subculture | leisure-resort — but if the garment's function isn't captured by these terms, use your own concise label (e.g. "dance", "hunting", "nursing", "pilgrimage"). Use ["none"] only if truly no social function applies.
"motif_family": Array of 1-3 motif families: geometric | floral | paisley | chevron-zigzag | spiral-scroll | animal-figurative | bird-figurative | mythological | calligraphic | lattice-trellis | medallion | stripe-band | dot-spot | tree-of-life | cloud-wave | star-celestial | heraldic | abstract-organic | none

=== KNOWLEDGE GRAPH FIELDS ===

"designer": Name of the designer, maker, or design house if known or inferable from the title/description. String or null. (e.g. "Vivienne Westwood", "Worth", "Issey Miyake")
"influence_references": Array of 1-3 specific historical or cultural references this garment draws from. Be precise — name the era, movement, culture, or garment type being referenced. (e.g. ["1890s leg-of-mutton sleeve", "Japanese obi wrapping", "Edwardian mourning dress"]). Use null if the garment is purely of its own moment with no visible backward reference.
"production_mode": haute couture | ready-to-wear | handmade | mass-produced | one-of-a-kind | artisan-craft | null
"material_origin": Geographic origin of the primary textile if known or strongly inferable. Distinct from the garment's culture — a French dress made with Indian chintz = culture "French", material_origin "India". String or null.
"garment_system": Array of other garments this piece requires, implies, or belongs to as an ensemble. (e.g. ["corset", "chemise", "petticoat"] for a Victorian evening gown, ["choli blouse"] for a sari, ["waistcoat", "cravat"] for a Regency coat). Use null if the garment is self-contained.
"named_movements": Array of 1-2 specific design or cultural movements beyond the era label. (e.g. ["Japonisme", "Aesthetic Movement"], ["Memphis Group"], ["Arts and Crafts"], ["Orientalism"], ["Bloomsbury Group"]). Use null if no specific movement applies.

"display_title": A concise, descriptive title (5-10 words) that a person could use to identify this item. Include the most distinctive attributes: material, color, garment type, and one defining feature. If the original title is already specific and descriptive, keep it unchanged. Do NOT include dates or era names. (e.g. "Burgundy Silk Velvet Fragment with Brocade Palmettes", "Sage Green Cotton Crew Neck T-Shirt", "Black Leather Double-Breasted Biker Jacket")

"low_confidence_fields": Array of field names where you are uncertain or inferring rather than observing. (e.g. ["designer", "material_origin", "decade"]). Use an empty array [] if you are confident in all fields.

If a field genuinely cannot be determined, leave it null. Do not guess. Return ONLY valid JSON, no markdown."""

        return [
            {"type": "text", "text": static_instructions, "cache_control": {"type": "ephemeral"}}
        ]

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

        prompt = f"""Analyze this item and return the JSON object specified in your instructions.

**Item Details (from museum/source records — may be incomplete or inaccurate):**
- Title: {title}
- Source category: {category}"""

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
        for key in ('fp_category', 'nickname', 'silhouette', 'neckline', 'waistline', 'length', 'sleeve_length', 'opening_type', 'textile_pattern'):
            val = existing_fields.get(key)
            if val:
                struct_context.append(f"- {key}: {val}")

        for key in ('textile_finishing', 'garment_parts', 'decorations'):
            val = existing_fields.get(key)
            if val and isinstance(val, list) and val:
                struct_context.append(f"- {key}: {', '.join(val)}")

        prompt = f"""Analyze this item and return the JSON object specified in your instructions.

**Item Details (from expert-annotated dataset — structural fields are pre-filled, do NOT change them):**
- Title: {title}
- Source category: {category}

**Expert-annotated structural attributes (already correct):**
{chr(10).join(struct_context) if struct_context else '(none)'}

Fill in all fields from your instructions. Keep expert-annotated structural fields as provided above."""

        content = self._build_image_content(image_data_url)

        content.append({
            "type": "text",
            "text": prompt
        })

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1200,
            temperature=0.5,
            system=self._build_enrichment_system_prompt(),
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
            if 'era' in creative:
                creative['era'] = normalize_era(creative.get('era'))
        except json.JSONDecodeError as e:
            print(f"  JSON parse error: {e}")
            creative = {
                "era": None, "decade": None,
                "style_tags": ["casual", "everyday"],
                "colors": ["unknown"], "material": "unknown",
                "season": "all-season", "garment_type": category,
                "vibe": "casual", "fit_style": "standard",
                "vibe_axes": {},
                "occasion": "everyday",
                "ai_description": f"{title} - modern {category} for everyday wear"
            }

        # Merge: keep existing structured fields, add creative fields
        merged = dict(existing_fields)
        for key in ('era', 'decade', 'culture', 'style_tags', 'colors', 'material', 'season', 'garment_type', 'vibe', 'fit_style', 'occasion', 'ai_description', 'vibe_axes', 'construction_technique', 'social_function', 'motif_family'):
            merged[key] = creative.get(key)

        # Fill in structural fields only if not already expert-annotated
        for key in ('silhouette', 'neckline', 'waistline', 'length', 'sleeve_length', 'opening_type', 'textile_pattern'):
            if not merged.get(key) and creative.get(key):
                merged[key] = creative[key]

        # Array fields — fill if empty
        for key in ('textile_finishing', 'garment_parts', 'decorations'):
            if not merged.get(key) and creative.get(key):
                merged[key] = creative[key]

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
            "era": None,
            "decade": None,
            "style_tags": [],
            "colors": [],
            "material": None,
            "season": None,
            "garment_type": category.lower() if category else None,
            "vibe_scores": {},
            "fit_style": None,
            "occasion": None,
            "ai_description": f"{title} - {category}",
            "construction_technique": [],
            "social_function": [],
            "motif_family": ["none"],
            "low_confidence_fields": ["all"],
        }

    @staticmethod
    def build_rich_text(product_data: Dict, enrichment: Dict) -> str:
        """
        Build natural-language text for embedding.
        Combines Fashionpedia taxonomy terms with creative descriptions.
        Max ~384 tokens for all-mpnet-base-v2.
        """

        parts = []

        # Display title first if available — more descriptive than raw title
        display_title = enrichment.get('display_title')
        if display_title:
            parts.append(display_title + ".")

        # ai_description — richest, most search-friendly content
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

        # Style tags
        style_tags = enrichment.get('style_tags', [])
        if style_tags:
            parts.append(f"{', '.join(style_tags)}.")

        # Axis-based vibe poles
        vibe_scores = enrichment.get('vibe_scores', {})
        if isinstance(vibe_scores, str):
            try:
                vibe_scores = json.loads(vibe_scores)
            except (json.JSONDecodeError, TypeError):
                vibe_scores = {}
        if vibe_scores and isinstance(vibe_scores, dict):
            poles = [v[0] for v in vibe_scores.values() if isinstance(v, list) and len(v) >= 1]
            if poles:
                parts.append(", ".join(poles) + ".")

        # Textile details and occasion
        extras = []
        if enrichment.get('fit_style'):
            extras.append(enrichment['fit_style'])
        tp = enrichment.get('textile_pattern', '')
        if isinstance(tp, list):
            tp = tp[0] if tp else ''
        if tp and tp != 'plain':
            extras.append(str(tp) + " pattern")
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

        # Cross-cultural bridge fields
        ct = enrichment.get('construction_technique', [])
        if isinstance(ct, str):
            try:
                ct = json.loads(ct)
            except (json.JSONDecodeError, TypeError):
                ct = [ct] if ct else []
        if ct:
            parts.append(f"Construction: {', '.join(ct)}.")

        sf = enrichment.get('social_function', [])
        if isinstance(sf, str):
            try:
                sf = json.loads(sf)
            except (json.JSONDecodeError, TypeError):
                sf = [sf] if sf else []
        if sf and sf != ['none']:
            parts.append(f"Function: {', '.join(sf)}.")

        mf = enrichment.get('motif_family', [])
        if isinstance(mf, str):
            try:
                mf = json.loads(mf)
            except (json.JSONDecodeError, TypeError):
                mf = [mf] if mf else []
        if mf and mf != ['none']:
            parts.append(f"Motifs: {', '.join(mf)}.")

        # Knowledge graph fields
        designer = enrichment.get('designer')
        if designer:
            parts.append(f"Designer: {designer}.")

        influences = enrichment.get('influence_references', [])
        if isinstance(influences, str):
            try:
                influences = json.loads(influences)
            except (json.JSONDecodeError, TypeError):
                influences = [influences] if influences else []
        if influences:
            parts.append(f"Influences: {', '.join(influences)}.")

        movements = enrichment.get('named_movements', [])
        if isinstance(movements, str):
            try:
                movements = json.loads(movements)
            except (json.JSONDecodeError, TypeError):
                movements = [movements] if movements else []
        if movements:
            parts.append(f"Movements: {', '.join(movements)}.")

        return " ".join(parts)

    # Internal metadata keys to exclude from narrative prompts
    # Keys in shared_entities that are metadata, not displayable entity data
    _SHARED_ENTITIES_EXCLUDE = {
        'lineage_reference', 'lineage_match_score', 'match_method', 'image_similarity',
    }

    # Human-readable labels for entity types
    _ENTITY_LABELS = {
        'designer': 'Designer',
        'named_movements': 'Movement',
        'influence_references': 'Shared influences',
        'construction_technique': 'Construction',
        'social_function': 'Function',
        'garment_system': 'Worn with',
        'motif_family': 'Motif',
    }

    @staticmethod
    def _format_shared_entities(shared: dict) -> str:
        """Format shared_entities dict as readable text for the narrative prompt.
        Groups by entity type with human-readable labels."""
        if not shared:
            return "none identified"
        parts = []
        for key, val in shared.items():
            if key in ClaudeEnricher._SHARED_ENTITIES_EXCLUDE:
                continue
            label = ClaudeEnricher._ENTITY_LABELS.get(key, key.replace('_', ' '))
            if isinstance(val, list):
                parts.append(f"{label}: {', '.join(str(v) for v in val)}")
            elif isinstance(val, (int, float, bool)):
                continue  # skip numeric/boolean metadata
            else:
                parts.append(f"{label}: {val}")
        return "; ".join(parts) if parts else "none identified"

    async def generate_bridge_narrative_async(
        self, item_a: dict, item_b: dict, shared_entities: dict,
        connection_mode: str = 'shared_entity',
        crossing_type: str | None = None,
        year_gap: int | None = None,
        directed: bool = False,
    ) -> str:
        """Generate a 2-3 sentence editorial narrative for a style bridge.

        One adaptive prompt for all bridge types. The shared_entities dict
        provides the substance — Claude narrates the path between two garments.
        Uses product images when available for visual specificity.
        """

        # One-liner per product
        def _one_liner(item):
            title = item.get('display_title') or item.get('title') or 'untitled'
            parts = []
            if item.get('era'):
                parts.append(item['era'])
            if item.get('culture'):
                parts.append(item['culture'])
            if item.get('material'):
                parts.append(item['material'])
            context = ", ".join(parts)
            return f"{title} ({context})" if context else title

        item_a_line = _one_liner(item_a)
        item_b_line = _one_liner(item_b)

        # Format what they share
        shared_text = self._format_shared_entities(shared_entities)
        if shared_text == "none identified" and connection_mode == 'visual_echo':
            shared_text = "visual form — see the images"

        # Distance context
        distance_parts = []
        if year_gap is not None and year_gap > 0:
            distance_parts.append(f"{year_gap} years apart")
        elif year_gap == 0:
            distance_parts.append("same era")
        if crossing_type and 'culture' in crossing_type and 'category' in crossing_type:
            distance_parts.append("different cultures and garment types")
        elif crossing_type and 'culture' in crossing_type:
            distance_parts.append("different cultures")
        elif crossing_type == 'cross_category':
            distance_parts.append("different garment types")
        else:
            if not distance_parts:
                distance_parts.append("same context")
        distance_line = " · ".join(distance_parts)

        # Lineage-specific context
        lineage_note = ""
        if connection_mode == 'lineage' and directed:
            ref = shared_entities.get('lineage_reference', '')
            if ref:
                lineage_note = f'\nItem B references "{ref}" — Item A is that tradition.'

        # Visual echo context
        visual_note = ""
        if connection_mode == 'visual_echo':
            visual_note = "\nThese garments look strikingly alike despite different origins. What visual quality connects them?"

        # Image context — accurate about what Claude can see
        img_a = item_a.get('primary_image')
        img_b = item_b.get('primary_image')
        if img_a and img_b:
            image_note = "You can see both garments above. Use what you see — specific visual details, not just the metadata."
        elif img_a:
            image_note = "You can see garment A above. Use visual details from the image for A; rely on metadata for B."
        elif img_b:
            image_note = "You can see garment B above. Use visual details from the image for B; rely on metadata for A."
        else:
            image_note = ""

        # One system prompt for all bridge types (cacheable)
        system_msg = [{"type": "text", "cache_control": {"type": "ephemeral"}, "text": (
            "You are a sharp fashion writer — think Cathy Horyn or Robin Givhan. "
            "You notice what most people miss. You write with precision and wit. "
            "No museum-label voice. No 'showcases' or 'exemplifies' or 'transcends'. "
            "Write like you're pointing something out to a smart friend.\n\n"
            "TASK: You will be shown two garments that are connected through shared design DNA — "
            "a technique, a movement, a designer, a visual echo across time. Write 2-3 sentences. "
            "Tell the story of the connection: what do they share, what's the distance between them, "
            "and what does the connection reveal? Be specific about these garments. No filler."
        )}]

        prompt = f"""Item A: {item_a_line}
Item B: {item_b_line}

Distance: {distance_line}
They share: {shared_text}{lineage_note}{visual_note}
{image_note}"""

        # Build content blocks: images first (if available), then text
        content = []
        if img_a:
            content.extend(self._build_image_content(img_a))
        if img_b:
            content.extend(self._build_image_content(img_b))
        content.append({"type": "text", "text": prompt})

        response = await self.async_client.messages.create(
            model=self.model,
            max_tokens=250,
            temperature=0.7,
            system=system_msg,
            messages=[
                {"role": "user", "content": content}
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
