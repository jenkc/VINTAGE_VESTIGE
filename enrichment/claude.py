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

VIBE_VOCABULARY = """
CONTROLLED VIBE VOCABULARY (pick only from these terms):

Each term is followed by its definition and the aesthetic argument it makes.
Assign terms that reflect what the garment is ARGUING, not just what it looks like.

AXIS 1 — Volume and Silhouette
(The garment's relationship to the body through shape and mass)

  - Exaggerated Volume     — structural mass exceeds functional necessity; 
    the outline is the subject, not the body beneath.
    Panniers, crinolines, puff sleeves, Comme des Garçons padding.
    The argument: the garment itself is the subject.

  - Column Minimalism      — unbroken vertical line, body-skimming or body-revealing,
    no structural intervention between fabric and form.
    Fortuny, 1960s shift, The Row.
    The argument: the body is sufficient.

  - Empire Suspension      — high waistline releases the body below; fabric falls from
    a single gathering point beneath the bust. Neoclassical,
    Regency, 1910s reform dress, certain 1960s revivals.
    The argument: liberation from below.

  - Constructed Armor      — rigid or semi-rigid structure holds the body in a
    predetermined shape; garment as exoskeleton. Stays,
    corsetry, McQueen tailoring, Thom Browne.
    The argument: the body must be managed.

  - Draped Fluidity        — fabric organized by gravity and body movement, not
    structure; no fixed silhouette. Greek chiton, Vionnet
    bias cut, Issey Miyake pleats.
    The argument: the body and fabric are in conversation.

  - Layered Accumulation   — multiple garments or fabric weights building depth;
    no single silhouette readable. Medieval layering,
    Rei Kawakubo, certain folk traditions.
    The argument: identity is cumulative.

AXIS 2 — Ornament and Surface
(What the garment does at its surface — decoration, material, texture)

  - Maximalist Ornament    — surface decoration exceeds structural function; the
    ornament is the primary aesthetic event. Rococo
    embroidery, Valentino couture, Victorian beading.
    The argument: excess is meaning.

  - Austere Restraint      — deliberate removal of decoration; surface communicates
    through absence. Quaker dress, Japanese minimalism,
    Jil Sander.
    The argument: restraint is its own statement.

- Handcraft Visibility   — surface makes its own making visible; evidence of human
    labor is the aesthetic content. Arts and Crafts dress,
    folk embroidery, contemporary slow fashion.
    The argument: the hand that made this matters.

- Material Luxury        — communication through inherent material richness, not
    applied decoration. Heavy silk, rare fur, fine wool,
    certain contemporary leather goods.
    The argument: substance speaks louder than ornament.

  - Pattern as Language    — surface organized by repeating motifs carrying cultural
    or symbolic content. Tartan, toile, ikat, Liberty prints.
    The argument: pattern is a form of speech.

  - Transparency and Revelation — deliberate use of sheer or open materials to
    suggest or reveal what is beneath. Victorian lace,
    1970s chiffon, contemporary mesh.
    The argument: concealment and revelation are simultaneous.

AXIS 3 — Body Relationship
(The ideological relationship the garment proposes between itself and the body)

  - Body Liberation        — designed to free the body from restriction; refuses
    constraint. Reform dress, 1920s drop waist, 1970s
    jersey, athletic crossover.
    The argument: the body should move freely.

  - Body Transformation    — designed to reshape the body into a culturally preferred
    form. Corsetry, padding, foundation garments, certain
    contemporary shapewear aesthetics.
    The argument: the natural body is insufficient.

  - Body Concealment       — deliberately obscures the body's form; refuses the gaze.
    Certain religious dress, 1980s power suiting,
    contemporary modest fashion, Balenciaga volume.
    The argument: the body is private.

  - Body Display           — stages the body for viewing; makes it the subject of
    attention. Court dress décolletage, 1950s swimwear,
    contemporary bodycon.
    The argument: the body is public.

AXIS 4 — Cultural Register
(The social and cultural argument — class, nature, ceremony, transgression)

  - Pastoral Naturalism    — invokes nature, rural life, or pre-industrial simplicity,
    genuine or constructed. 18th century pastoral costume,
    Arts and Crafts dress, 1970s folk revival, cottagecore.
    The argument: nature is preferable to culture.

  - Ceremonial Formalism   — primary function is to mark ritual occasion, separate it
    from the everyday. Court dress, ecclesiastical vestment,
    wedding dress across cultures.
    The argument: some moments require dedicated clothing.

  - Dark Romanticism       — aestheticizes melancholy, mortality, or the uncanny.
    Victorian mourning dress, Gothic subculture, certain
    Alexander McQueen, dark academia.
    The argument: darkness is beautiful.

  - Transgressive Subversion — deliberately violates the sartorial norms of its
    moment; uses dress as protest or provocation. Bloomers,
    punk, early queer fashion, certain streetwear.
    The argument: clothing can refuse.

- Nostalgic Revival      — consciously quotes a previous era; the historical
    reference is the primary aesthetic content. Victorian
    revival in Edwardian dress, 1930s Hollywood glamour
    revivals, contemporary vintage aesthetics.
    The argument: the past was better, or at least richer.

  - Elite Distinction      — communicates social position through understatement, quality, and codes legible only to insiders.   Savile Row tailoring, old money aesthetics, quiet luxury.
  The argument: true status needs no announcement.

Assign:
  core_vibes:   1–3 terms (from any axis) that define this piece's primary arguments
  bridge_vibes: 1–2 terms most likely to find echoes across other eras — the argument
                this piece shares with garments centuries before or after it
  vibe_scores:  confidence for each assigned term (0.0–1.0)

Note on bridge_vibes: A term makes a good bridge_vibe when its argument is not
era-specific — when the same claim (e.g. "the body should move freely") has been
made in radically different historical moments. Axis 3 (Body Relationship) and
Axis 1 (Volume/Silhouette) terms tend to bridge well. Axis 4 (Cultural Register)
terms are often more era-specific and bridge less reliably.
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
            system="You are enriching a historical fashion record for Vintage Vestige, a knowledge graph that connects museum archival pieces to modern fashion. You are a fashion historian and vintage style expert. Return only valid JSON, no markdown.",
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

        prompt = f"""Analyze this item and provide rich metadata that bridges museum catalog language with how modern people search for fashion inspiration.

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

        era_prompt = build_era_prompt_section()

        prompt += f"""

Return a JSON object with ALL fields below. Pick from the given options or null if not applicable.

NOTE: For non-Western garments (sari, kimono, hanbok, kaftan, dashiki, cheongsam, huipil, etc.), use the garment's own name in "garment_type" and "nickname". Use null for structural fields (neckline, waistline, etc.) that don't apply to the garment's construction. Pick the closest fp_category or use "dress" / "coat" as rough approximation.

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

"era": EXACT name from this list:
{era_prompt}
"decade": "e.g. "1780s", "1920s", "2010s" or null if not clear"
"style_tags": 3-5 tags mixing historical and modern aesthetics (e.g. "flapper", "Rococo", "cottagecore", "formal", "everyday", "ceremonial", "workwear", "sportswear", "eveningwear")
"colors": 2-4 specific colors visible | inferred from description (e.g. "navy blue", "cream", "burgundy") | "multi-colored"
"material": Primary fabric (e.g. "silk taffeta", "wool broadcloth")
"season": spring/summer | fall/winter | all-season | evening
"garment_type": Natural language (e.g. "bustle evening gown", "tailored riding jacket")
{VIBE_VOCABULARY}
"core_vibes": ["1-3 terms from controlled vocabulary above"],
"bridge_vibes": ["1-2 terms most likely to connect across eras"],
"vibe_scores": {{"term": confidence_float}},
"fit_style": Fit description (e.g. "corseted fitted", "flowing draped")
"occasion": e.g. "formal evening", "everyday wear", "garden party"
"ai_description": 100-150 words placing this piece in context, using assigned vibe terms. Specificity matters more than prose quality.

=== CROSS-CULTURAL BRIDGE FIELDS ===

"construction_technique": Array of 1-3 techniques: hand-embroidery | machine-embroidery | hand-weaving | machine-weaving | knitting | crocheting | felting | draping | tailoring | resist-dyeing | block-printing | screen-printing | digital-printing | batik | tie-dye | quilting | smocking | pleating | lacework | beadwork | applique | tapestry | brocade-weaving | jacquard-weaving | hand-sewing | couture-construction | leather-working | metalwork | null
"social_function": Array of 1-2 social roles this garment serves. Prefer terms from this list: wedding | mourning | religious-ceremonial | court-formal | military-uniform | status-signaling | everyday-practical | workwear | sportswear | performance-costume | coming-of-age | festival-celebration | diplomatic-gift | academic-formal | protest-subculture | leisure-resort — but if the garment's function isn't captured by these terms, use your own concise label (e.g. "dance", "hunting", "nursing", "pilgrimage"). Use ["none"] only if truly no social function applies.
"motif_family": Array of 1-3 motif families: geometric | floral | paisley | chevron-zigzag | spiral-scroll | animal-figurative | bird-figurative | mythological | calligraphic | lattice-trellis | medallion | stripe-band | dot-spot | tree-of-life | cloud-wave | star-celestial | heraldic | abstract-organic | none

If a field genuinely cannot be determined, leave it null. Do not guess. Return ONLY valid JSON, no markdown."""

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

        prompt = f"""Analyze this fashion item and provide CREATIVE metadata for search discovery.

**Item:** {title}
**Category:** {category}

**Already-annotated structural attributes (expert-labeled, do NOT change these):**
{chr(10).join(struct_context) if struct_context else '(none)'}

Based on the image and attributes above, provide the creative/search-bridge fields AND any missing structural fields.
Think about: What modern aesthetic does this evoke? What would someone searching for this style type?

Return ONLY valid JSON with these fields:

=== MISSING STRUCTURAL FIELDS (infer from image, or null if not visible/applicable) ===

"silhouette": Pick ONE or null: a-line | pencil | straight | fit and flare | flare | trumpet | mermaid | balloon | bell | wide leg | peg | tent | tight fit | regular fit | loose fit | oversized
"neckline": Pick ONE or null: v-neck | crew neck | round neck | boat neck | scoop neck | square neckline | sweetheart | plunging | keyhole | halter neck | off-the-shoulder | one shoulder | turtle neck | cowl neck | high neck | collarless | surplice | u-neck | straight across
"waistline": Pick ONE or null: empire waistline | high waist | normal waist | low waist | dropped waistline | no waistline
"length": Pick ONE or null: above-the-hip | hip length | mini | above-the-knee | knee length | below the knee | midi | maxi | floor length
"sleeve_length": Pick ONE or null: sleeveless | short | elbow-length | three quarter | wrist-length
"opening_type": Pick ONE or null: single breasted | double breasted | zip-up | wrapping | lace up | no opening
"textile_pattern": Pick ONE: plain | floral | stripe | check | dot | geometric | paisley | abstract | houndstooth | herringbone | leopard | toile de jouy
"textile_finishing": Array of 0-3: distressed | quilted | pleated | ruched | cutout | slit | tiered | smocking | gathering | beaded | sequined | applique
"garment_parts": Array: hood | collar | lapel | epaulette | sleeve | pocket | buckle | zipper
"decorations": Array: applique | bead | bow | flower | fringe | ribbon | rivet | ruffle | sequin | tassel

=== CREATIVE / SEARCH-BRIDGE FIELDS ===

  "era": "EXACT name from taxonomy:\n""" + build_era_prompt_section() + """",
  "decade": "e.g. 2010s, 2020s, or null",
  "culture": "cultural/geographic influence (e.g. Western, Japanese, South Asian, African, Korean) or null",
  "style_tags": ["3-5 modern aesthetic tags"],
  "colors": ["2-4 specific colors"],
  "material": "primary fabric",
  "season": "spring/summer | fall/winter | all-season",
  "garment_type": "natural language (e.g. fitted blazer, flowy sundress)",
  {VIBE_VOCABULARY}
  "core_vibes": ["1-3 terms from controlled vocabulary above"],
  "bridge_vibes": ["1-2 terms most likely to connect across eras"],
  "vibe_scores": {{"term": confidence_float}},
  "fit_style": "fit description (e.g. relaxed oversized, structured tailored)",
  "occasion": "e.g. everyday casual, date night, office",
  "ai_description": 100-150 words placing this piece in context, using assigned vibe terms. Specificity matters more than prose quality.

=== CROSS-CULTURAL BRIDGE FIELDS ===

  "construction_technique": Array of 1-3 techniques: hand-embroidery | machine-embroidery | hand-weaving | machine-weaving | knitting | crocheting | felting | draping | tailoring | resist-dyeing | block-printing | screen-printing | digital-printing | batik | tie-dye | quilting | smocking | pleating | lacework | beadwork | applique | tapestry | brocade-weaving | jacquard-weaving | hand-sewing | couture-construction | leather-working | metalwork | null
  "social_function": Array of 1-2 social roles this garment serves. Prefer terms from this list: wedding | mourning | religious-ceremonial | court-formal | military-uniform | status-signaling | everyday-practical | workwear | sportswear | performance-costume | coming-of-age | festival-celebration | diplomatic-gift | academic-formal | protest-subculture | leisure-resort — but if the garment's function isn't captured by these terms, use your own concise label (e.g. "dance", "hunting", "nursing", "pilgrimage"). Use ["none"] only if truly no social function applies.
  "motif_family": Array of 1-3 motif families: geometric | floral | paisley | chevron-zigzag | spiral-scroll | animal-figurative | bird-figurative | mythological | calligraphic | lattice-trellis | medallion | stripe-band | dot-spot | tree-of-life | cloud-wave | star-celestial | heraldic | abstract-organic | none
"""

        content = self._build_image_content(image_data_url)

        content.append({
            "type": "text",
            "text": prompt
        })

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1200,
            temperature=0.5,
            system="You are a fashion stylist and trend expert. Return only valid JSON, no markdown.",
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
                "era": "Quiet Luxury", "decade": "2010s",
                "style_tags": ["casual", "everyday"],
                "colors": ["unknown"], "material": "unknown",
                "season": "all-season", "garment_type": category,
                "vibe": "casual", "fit_style": "standard",
                "core_vibes": [], "bridge_vibes": [], "vibe_scores": {},
                "occasion": "everyday",
                "ai_description": f"{title} - modern {category} for everyday wear"
            }

        # Merge: keep existing structured fields, add creative fields
        merged = dict(existing_fields)
        for key in ('era', 'decade', 'culture', 'style_tags', 'colors', 'material', 'season', 'garment_type', 'vibe', 'fit_style', 'occasion', 'ai_description', 'core_vibes', 'bridge_vibes', 'vibe_scores', 'construction_technique', 'social_function', 'motif_family'):
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
            "era": "Quiet Luxury",
            "decade": None,
            "style_tags": ["casual", "everyday"],
            "colors": ["unknown"],
            "material": "unknown",
            "season": "all-season",
            "garment_type": category.lower(),
            "vibe": "casual comfortable",
            "core_vibes": [],
            "bridge_vibes": [],
            "vibe_scores": {},
            "fit_style": "standard",
            "occasion": "everyday",
            "ai_description": f"{title} - {category} for everyday wear",
            "construction_technique": [],
            "social_function": [],
            "motif_family": ["none"],
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

        # Controlled vibe terms (when available, more consistent than free-form vibe)
        core = enrichment.get('core_vibes', [])
        bridge = enrichment.get('bridge_vibes', [])
        if core:
            parts.append(", ".join(core) + ".")
        if bridge:
            parts.append(", ".join(bridge) + ".")

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

        return " ".join(parts)

    @staticmethod
    def _format_shared_attributes(shared: dict) -> str:
        """Format shared_attributes dict as readable text for the prompt."""
        if not shared:
            return "none identified"
        parts = []
        for key, val in shared.items():
            label = key.replace('_', ' ')
            if isinstance(val, list):
                parts.append(f"{label}: {', '.join(str(v) for v in val)}")
            else:
                parts.append(f"{label}: {val}")
        return "; ".join(parts)

    @staticmethod
    def _narrative_closing(temporal_type: str | None, crossing_type: str | None,
                           connection_mode: str | None) -> str:
        """Return a varied closing instruction based on classification."""
        if connection_mode == 'contrast':
            return "Explain the tension between these opposing approaches."
        if connection_mode == 'resonance':
            return "Explain what echoes between them despite the distance."
        if temporal_type == 'echo':
            return "Explain how this design idea resurfaced across such a wide time gap."
        if temporal_type == 'transmission':
            return "Explain how this design language traveled across eras."
        if temporal_type == 'continuation':
            return "Explain how this design thread persisted within its era."
        if crossing_type and 'culture' in crossing_type:
            return "Explain how different cultures arrived at this shared design idea."
        if crossing_type == 'cross_category':
            return "Explain what connects these different garment types."
        return "Explain the design DNA they share."

    async def generate_bridge_narrative_async(
        self, item_a: dict, item_b: dict, shared_attributes: dict,
        connection_mode: str | None = None, contrast_pair: str | None = None,
        temporal_type: str | None = None, crossing_type: str | None = None,
        primary_axis: str | None = None,
    ) -> str:
        """Generate a 1-sentence narrative for a style bridge."""
        shared_text = self._format_shared_attributes(shared_attributes)

        # Mode-specific context line
        mode_hint = ""
        if connection_mode == 'contrast' and contrast_pair:
            mode_hint = f"Connection: CONTRAST on {contrast_pair}."
        elif connection_mode == 'resonance':
            mode_hint = "Connection: RESONANCE — same aesthetic language across time."
        elif connection_mode == 'affinity':
            mode_hint = "Connection: AFFINITY — shared structural DNA."

        # Vibes (core_vibes if available)
        vibes_a = item_a.get('core_vibes') or []
        vibes_b = item_b.get('core_vibes') or []
        vibe_line = ""
        if vibes_a or vibes_b:
            vibe_line = (
                f"Vibes A: {', '.join(vibes_a) if vibes_a else 'none'} | "
                f"Vibes B: {', '.join(vibes_b) if vibes_b else 'none'}"
            )

        closing = self._narrative_closing(temporal_type, crossing_type, connection_mode)

        lines = [
            f"ITEM A: {item_a['title']}",
            f"Era: {item_a.get('era', 'unknown')} | Culture: {item_a.get('culture', 'unknown')}",
            f"Material: {item_a.get('material', 'unknown')} | Silhouette: {item_a.get('silhouette', 'unknown')}",
            f"Function: {item_a.get('social_function', 'unknown')}",
            "",
            f"ITEM B: {item_b['title']}",
            f"Era: {item_b.get('era', 'unknown')} | Culture: {item_b.get('culture', 'unknown')}",
            f"Material: {item_b.get('material', 'unknown')} | Silhouette: {item_b.get('silhouette', 'unknown')}",
            f"Function: {item_b.get('social_function', 'unknown')}",
            "",
            f"Shared attributes: {shared_text}",
        ]
        if vibe_line:
            lines.append(vibe_line)
        if mode_hint:
            lines.append(mode_hint)
        lines.append("")
        lines.append(closing)
        prompt = "\n".join(lines)

        if connection_mode == 'contrast':
            system_msg = "You are a fashion historian. Write exactly two sentences, max 60 words total. First sentence: what they share. Second sentence: how they diverge. No quotes, no preamble."
        else:
            system_msg = "You are a fashion historian. Write exactly one sentence, max 40 words. No quotes, no preamble."

        response = await self.async_client.messages.create(
            model=self.model,
            max_tokens=200,
            temperature=0.6,
            system=system_msg,
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
