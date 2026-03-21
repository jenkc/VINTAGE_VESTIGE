from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Create PDF
doc = SimpleDocTemplate(
    "MindCap_Research_Validation_Roadmap.pdf",
    pagesize=letter,
    rightMargin=0.75*inch,
    leftMargin=0.75*inch,
    topMargin=0.75*inch,
    bottomMargin=0.75*inch
)

# Styles
styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=24,
    textColor=colors.HexColor('#EC4899'),
    spaceAfter=30,
    alignment=TA_CENTER
)
heading1_style = ParagraphStyle(
    'CustomHeading1',
    parent=styles['Heading1'],
    fontSize=16,
    textColor=colors.HexColor('#A78BFA'),
    spaceAfter=12,
    spaceBefore=12
)
heading2_style = ParagraphStyle(
    'CustomHeading2',
    parent=styles['Heading2'],
    fontSize=14,
    textColor=colors.HexColor('#6B7280'),
    spaceAfter=10,
    spaceBefore=10
)
body_style = ParagraphStyle(
    'CustomBody',
    parent=styles['BodyText'],
    fontSize=10,
    alignment=TA_JUSTIFY,
    spaceAfter=6
)
code_style = ParagraphStyle(
    'Code',
    parent=styles['Code'],
    fontSize=8,
    leftIndent=20,
    spaceAfter=6
)

# Build document
story = []

# Title page
story.append(Spacer(1, 1*inch))
story.append(Paragraph("🧠", title_style))
story.append(Paragraph("MindCap", title_style))
story.append(Paragraph("Research &amp; Validation Roadmap", heading1_style))
story.append(Spacer(1, 0.3*inch))
story.append(Paragraph("Version 1.0 | February 2024", body_style))
story.append(Paragraph("Timeline: 3-4 months to validated MVP", body_style))
story.append(PageBreak())

# Executive Summary
story.append(Paragraph("Executive Summary", heading1_style))
story.append(Paragraph(
    "You are currently in the <b>research and validation phase</b>, not ready to launch. "
    "This roadmap provides a structured 16-week plan to validate your core algorithms before "
    "considering a public launch.",
    body_style
))
story.append(Spacer(1, 0.2*inch))
story.append(Paragraph(
    "<b>Key Insight:</b> You thought you were at 'polish and launch' but you're actually at "
    "'validate core algorithms.' This is good—you caught it before launching something broken.",
    body_style
))
story.append(Spacer(1, 0.3*inch))

# Current Reality
story.append(Paragraph("Current Reality Check", heading2_style))
story.append(Paragraph("<b>What You Have:</b>", body_style))
story.append(Paragraph("✅ Extension infrastructure (Plasmo, IndexedDB, sync)", body_style))
story.append(Paragraph("✅ Backend architecture (FastAPI, Supabase)", body_style))
story.append(Paragraph("✅ Privacy-first design", body_style))
story.append(Paragraph("✅ Clear differentiation (rabbit holes as features)", body_style))
story.append(Paragraph("✅ 56,000 Firefox history records for testing", body_style))
story.append(Spacer(1, 0.2*inch))

story.append(Paragraph("<b>What You Need:</b>", body_style))
story.append(Paragraph("🔲 Validated keyword extraction (80%+ accuracy)", body_style))
story.append(Paragraph("🔲 Validated session detection (90%+ accuracy)", body_style))
story.append(Paragraph("🔲 Validated rabbit hole classification (75%+ accuracy)", body_style))
story.append(Paragraph("🔲 Working topic chain reconstruction", body_style))
story.append(Paragraph("🔲 Clear, compelling visualization", body_style))
story.append(Paragraph("🔲 Real user feedback (5+ people saying 'I'd use this')", body_style))

story.append(PageBreak())

# Phase 1: Algorithm Development
story.append(Paragraph("Phase 1: Algorithm Development (Weeks 1-6)", heading1_style))

# Week 1-2
story.append(Paragraph("Week 1-2: Keyword Extraction Validation", heading2_style))
story.append(Paragraph("<b>Goal:</b> 80%+ accuracy on extracting topics from page titles", body_style))
story.append(Spacer(1, 0.1*inch))

activities = [
    "Create validation notebook with 100-sample test set",
    "Port TypeScript algorithm to Python for testing",
    "Manual review of all 100 extractions",
    "Calculate accuracy metrics",
    "Identify failure patterns",
    "Iterate on algorithm"
]
for activity in activities:
    story.append(Paragraph(f"• {activity}", body_style))

story.append(Spacer(1, 0.2*inch))
story.append(Paragraph("<b>Common Issues You'll Find:</b>", body_style))
issues = [
    "Domain names appearing as keywords (github, reddit)",
    "Generic words not filtered (tutorial, guide, best)",
    "Missing compound terms (machine learning → machine, learning)",
    "Comparison patterns not detected (X vs Y)"
]
for issue in issues:
    story.append(Paragraph(f"• {issue}", body_style))

story.append(Spacer(1, 0.2*inch))
story.append(Paragraph("<b>Success Criteria:</b>", body_style))
story.append(Paragraph("Accuracy = (Good + Okay) / Total ≥ 80%", code_style))
story.append(Paragraph("Where Good = captures right topics, Okay = acceptable, Bad = wrong", body_style))

story.append(Spacer(1, 0.2*inch))
story.append(Paragraph("<b>Time Allocation:</b>", body_style))
time_table = [
    ['Day', 'Activity'],
    ['1-2', 'Set up notebook, run extraction'],
    ['3-4', 'Manual review (50 samples per day)'],
    ['5-6', 'Analysis and iteration'],
    ['7', 'Update extension code']
]
t = Table(time_table, colWidths=[1*inch, 4.5*inch])
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3E8FF')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#6B21A8')),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 10),
    ('FONTSIZE', (0, 1), (-1, -1), 9),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
]))
story.append(t)

story.append(PageBreak())

# Week 3-4
story.append(Paragraph("Week 3-4: Session Detection Validation", heading2_style))
story.append(Paragraph("<b>Goal:</b> 90%+ correct session boundaries", body_style))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("<b>Daily Browsing Scenarios:</b>", body_style))
story.append(Spacer(1, 0.1*inch))

scenarios = [
    ("Monday: Deep Research", "2-hour focused research, test if coffee break splits session"),
    ("Tuesday: Fragmented Browsing", "Multiple short sessions throughout day, test time gaps"),
    ("Wednesday: Rabbit Hole", "Start with one topic, end elsewhere, test topic drift"),
    ("Thursday: Comparison Shopping", "Research products, test back-and-forth navigation"),
    ("Friday: Work + Interruption", "Focused work interrupted by distraction, test context switch")
]

for day, desc in scenarios:
    story.append(Paragraph(f"<b>{day}:</b> {desc}", body_style))

story.append(Spacer(1, 0.2*inch))
story.append(Paragraph("<b>Metrics to Track:</b>", body_style))

metrics_table = [
    ['Metric', 'Formula', 'Target'],
    ['Boundary Accuracy', 'Correct boundaries / Total', '90%+'],
    ['Type Accuracy', 'Correct type / Total', '70%+'],
    ['False Splits', 'Incorrectly split / Total', '<10%'],
    ['False Merges', 'Incorrectly merged / Total', '<5%']
]
t = Table(metrics_table, colWidths=[2*inch, 2*inch, 1.5*inch])
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#DBEAFE')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 9),
    ('FONTSIZE', (0, 1), (-1, -1), 8),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
]))
story.append(t)

story.append(Spacer(1, 0.2*inch))
story.append(Paragraph("<b>Parameters to Tune:</b>", body_style))
story.append(Paragraph("maxGapMinutes: 30 (tune: 20? 30? 45?)", code_style))
story.append(Paragraph("topicShiftThreshold: 0.2 (keyword overlap)", code_style))
story.append(Paragraph("videoGapTolerance: 60 (longer gaps during video)", code_style))

story.append(PageBreak())

# Week 5-6
story.append(Paragraph("Week 5-6: Rabbit Hole Classification", heading2_style))
story.append(Paragraph("<b>Goal:</b> 75%+ agreement between manual and algorithm classification", body_style))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("<b>The 4 Rabbit Hole Types:</b>", body_style))

types_table = [
    ['Type', 'Characteristics', 'Example'],
    ['Coherent Deep Dive', 'High depth, low spread, high coherence', 'kubernetes → networking → TCP → OSI'],
    ['Wandering Journey', 'High depth, high spread, logical steps', 'hooks → redux → event sourcing → DDD'],
    ['Tangent Hopper', 'Random jumps, "how did I get here?"', 'docker → pizza → renaissance → crypto'],
    ['Focused Exploration', 'Low depth, high branching', 'kubernetes → (docs, video, reddit, SO)']
]
t = Table(types_table, colWidths=[1.5*inch, 2*inch, 2*inch])
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FEF3C7')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#78350F')),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 9),
    ('FONTSIZE', (0, 1), (-1, -1), 8),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
]))
story.append(t)

story.append(Spacer(1, 0.2*inch))
story.append(Paragraph("<b>Activities:</b>", body_style))
activities = [
    "Collect 20 real rabbit hole sessions from your browsing",
    "Manually classify each before looking at algorithm output",
    "Compare manual vs algorithm classification",
    "Create confusion matrix",
    "Tune classification thresholds",
    "Document each type clearly"
]
for activity in activities:
    story.append(Paragraph(f"• {activity}", body_style))

story.append(PageBreak())

# Phase 2
story.append(Paragraph("Phase 2: Visualization Development (Weeks 9-12)", heading1_style))

story.append(Paragraph("Week 9-10: Design Explorations", heading2_style))
story.append(Paragraph(
    "Now that your data is good, how do you show it? Explore 4 visualization options:",
    body_style
))
story.append(Spacer(1, 0.1*inch))

viz_options = [
    ("Linear Timeline", "Simple, easy to understand, mobile-friendly", "RECOMMENDED"),
    ("Tree Diagram", "Shows branching clearly", "For complex cases"),
    ("Sankey Diagram", "Shows time + flow", "Advanced"),
    ("Network Graph", "Shows connections", "Post-MVP")
]

for option, desc, note in viz_options:
    story.append(Paragraph(f"<b>{option}</b> ({note}): {desc}", body_style))

story.append(Spacer(1, 0.2*inch))
story.append(Paragraph("<b>Your Task:</b>", body_style))
story.append(Paragraph("1. Mock up all 4 options (Figma or hand-drawn)", body_style))
story.append(Paragraph("2. Test with your own rabbit hole data", body_style))
story.append(Paragraph("3. Ask: 'Which one makes me go aha!'?", body_style))
story.append(Paragraph("4. Pick ONE for MVP", body_style))

story.append(Spacer(1, 0.3*inch))
story.append(Paragraph("Week 11-12: Build One Visualization", heading2_style))
story.append(Paragraph(
    "Pick ONE visualization and build it properly. Don't build all 4—that's scope creep.",
    body_style
))
story.append(Spacer(1, 0.1*inch))
story.append(Paragraph("<b>Iterate Until:</b>", body_style))
story.append(Paragraph("• You can understand the flow at a glance", body_style))
story.append(Paragraph("• The visualization reveals something interesting", body_style))
story.append(Paragraph("• You'd want to share it with someone", body_style))

story.append(PageBreak())

# Phase 3
story.append(Paragraph("Phase 3: Self-Dogfooding (Weeks 13-16)", heading1_style))

story.append(Paragraph("Week 13-14: Use It Daily", heading2_style))
story.append(Paragraph("<b>Goal:</b> Live with your own tool for 2 weeks", body_style))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("<b>Daily Routine:</b>", body_style))
routine = [
    "Browse normally (don't change behavior)",
    "Check dashboard once per day",
    "Keep a journal of observations"
]
for item in routine:
    story.append(Paragraph(f"• {item}", body_style))

story.append(Spacer(1, 0.2*inch))
story.append(Paragraph("<b>Red Flags:</b>", body_style))
red_flags = [
    "⚠️ You stop checking after 3 days → Core value isn't there",
    "⚠️ You check but don't learn anything → Insights are weak",
    "⚠️ You're embarrassed by rabbit holes → Framing is wrong"
]
for flag in red_flags:
    story.append(Paragraph(flag, body_style))

story.append(Spacer(1, 0.2*inch))
story.append(Paragraph("<b>Green Flags:</b>", body_style))
green_flags = [
    "✅ You check daily without reminders",
    "✅ You screenshot rabbit holes to share",
    "✅ You learn something about yourself",
    "✅ You want to show it to friends"
]
for flag in green_flags:
    story.append(Paragraph(flag, body_style))

story.append(Spacer(1, 0.3*inch))
story.append(Paragraph("Week 15-16: Show 5 Friends", heading2_style))
story.append(Paragraph("<b>Goal:</b> Validate with real users", body_style))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("<b>Pick 5 People Who:</b>", body_style))
story.append(Paragraph("• Browse a lot (knowledge workers, students, researchers)", body_style))
story.append(Paragraph("• Are comfortable with early software", body_style))
story.append(Paragraph("• Will give honest feedback", body_style))

story.append(Spacer(1, 0.2*inch))
story.append(Paragraph("<b>Process:</b>", body_style))
process = [
    "Install for them (sit with them, don't just send link)",
    "Have them browse for 3 days",
    "Review dashboard together",
    "Ask open-ended questions"
]
for step in process:
    story.append(Paragraph(f"{process.index(step)+1}. {step}", body_style))

story.append(PageBreak())

# Decision Point
story.append(Paragraph("Decision Point (Week 16)", heading1_style))

story.append(Paragraph("<b>Success Criteria:</b>", body_style))
story.append(Paragraph(
    "✅ <b>GO if:</b> 3 out of 5 find it interesting (7+ on 10-point scale), "
    "2 out of 5 would pay something, 1 out of 5 asks 'when can I use this?'",
    body_style
))
story.append(Spacer(1, 0.1*inch))
story.append(Paragraph(
    "🚨 <b>NO-GO if:</b> Less than 50% find it interesting, less than 30% would pay, "
    "fundamental confusion about concept",
    body_style
))

story.append(Spacer(1, 0.3*inch))
story.append(Paragraph("Option A: You Have Something (3+ friends loved it)", heading2_style))
story.append(Paragraph("<b>Next Steps:</b>", body_style))
story.append(Paragraph("1. Polish the MVP (2 weeks)", body_style))
story.append(Paragraph("2. Recruit 20 beta users (1 week)", body_style))
story.append(Paragraph("3. Launch in 6 weeks", body_style))
story.append(Paragraph("<b>Timeline to Launch:</b> 9 weeks from decision point", body_style))

story.append(Spacer(1, 0.2*inch))
story.append(Paragraph("Option B: Interesting But Not There Yet (1-2 friends loved it)", heading2_style))
story.append(Paragraph("<b>Next Steps:</b>", body_style))
story.append(Paragraph("1. Identify the gap (what's missing?)", body_style))
story.append(Paragraph("2. Build that one thing (4 weeks)", body_style))
story.append(Paragraph("3. Test with 5 more friends (2 weeks)", body_style))
story.append(Paragraph("4. Re-evaluate", body_style))
story.append(Paragraph("<b>Timeline to Launch:</b> 12-16 weeks from decision point", body_style))

story.append(Spacer(1, 0.2*inch))
story.append(Paragraph("Option C: Nobody Cares (Less than 1 friend loved it)", heading2_style))
story.append(Paragraph("<b>Pivot Options:</b>", body_style))
pivots = [
    "Different framing (not 'rabbit holes' but 'research patterns')",
    "Different audience (ADHD community, researchers, enterprise)",
    "Different product (weekly email, real-time nudges)",
    "Kill it (take learnings to new problem)"
]
for pivot in pivots:
    story.append(Paragraph(f"• {pivot}", body_style))

story.append(PageBreak())

# Success Metrics Summary
story.append(Paragraph("Success Metrics Summary", heading1_style))

metrics_table = [
    ['Phase', 'Week', 'Milestone', 'Success Criteria'],
    ['1', '2', 'Keyword extraction', '80%+ accuracy'],
    ['1', '4', 'Session detection', '90%+ boundaries'],
    ['1', '6', 'Rabbit hole classification', '75%+ types'],
    ['1', '8', 'Topic chains', '100% tree structure'],
    ['2', '10', 'Visualization', '"Whoa" reaction'],
    ['2', '12', 'Dashboard', 'End-to-end works'],
    ['3', '14', 'Self-dogfooding', 'Daily use, interesting'],
    ['3', '16', 'User validation', '3/5 love it']
]
t = Table(metrics_table, colWidths=[0.6*inch, 0.6*inch, 2*inch, 2.3*inch])
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ECFDF5')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#065F46')),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 9),
    ('FONTSIZE', (0, 1), (-1, -1), 8),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')])
]))
story.append(t)

story.append(Spacer(1, 0.3*inch))
story.append(Paragraph("Critical Path Dependencies", heading2_style))
story.append(Paragraph(
    "Each phase depends on the previous. You cannot skip steps:",
    body_style
))
story.append(Spacer(1, 0.1*inch))
story.append(Paragraph("Keyword Extraction (2w) →", body_style))
story.append(Paragraph("Session Detection (2w) →", body_style))
story.append(Paragraph("Rabbit Hole Classification (2w) →", body_style))
story.append(Paragraph("Topic Chain Reconstruction (2w) →", body_style))
story.append(Paragraph("Visualization (2w) →", body_style))
story.append(Paragraph("Dashboard (2w) →", body_style))
story.append(Paragraph("Self-Dogfooding (2w) →", body_style))
story.append(Paragraph("User Validation (2w) →", body_style))
story.append(Paragraph("<b>GO/NO-GO DECISION</b>", body_style))

story.append(PageBreak())

# What NOT to Do
story.append(Paragraph("What NOT to Do", heading1_style))

dont_do = [
    ("Don't build the dashboard first", "You'll have nothing to show in it. Waste time on UI when algorithms are broken."),
    ("Don't perfect one thing for months", "80% accuracy is good enough. Diminishing returns after that."),
    ("Don't build all 4 visualizations", "Pick one, validate it works. Add others only if users ask."),
    ("Don't add new features", "No account linking, mobile app, or other patterns yet. Just rabbit holes, done well.")
]

for title, desc in dont_do:
    story.append(Paragraph(f"<b>❌ {title}</b>", body_style))
    story.append(Paragraph(desc, body_style))
    story.append(Spacer(1, 0.1*inch))

story.append(Spacer(1, 0.2*inch))
story.append(Paragraph("Parallel Work (What You CAN Do)", heading2_style))
story.append(Paragraph("While working on algorithms, you can:", body_style))

can_do = [
    "✅ Build in public (tweet progress, share findings)",
    "✅ Design mockups (Figma doesn't require working code)",
    "✅ Write documentation (privacy policy, FAQ)",
    "✅ Plan marketing (landing page copy, Product Hunt assets)"
]
for item in can_do:
    story.append(Paragraph(item, body_style))

story.append(Spacer(1, 0.1*inch))
story.append(Paragraph("<b>But don't build code for these yet.</b> Focus on algorithms first.", body_style))

story.append(PageBreak())

# Timeline Summary
story.append(Paragraph("The Honest Timeline", heading1_style))

timeline_table = [
    ['Scenario', 'Timeline', 'Outcome'],
    ['Optimistic (everything works first try)', '16 weeks to beta', 'Ready to launch'],
    ['Realistic (normal iteration)', '20-24 weeks to beta', 'Ready to launch'],
    ['Pessimistic (major pivots)', '28+ weeks or never', 'Pivot or kill']
]
t = Table(timeline_table, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FEE2E2')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#7F1D1D')),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 9),
    ('FONTSIZE', (0, 1), (-1, -1), 8),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
]))
story.append(t)

story.append(Spacer(1, 0.2*inch))
story.append(Paragraph(
    "<b>Remember:</b> You're doing research, not just engineering. Research takes time.",
    body_style
))

story.append(Spacer(1, 0.3*inch))
story.append(Paragraph("Your Immediate Action Plan", heading2_style))

action_table = [
    ['Timeline', 'Action'],
    ['TODAY', 'Set up validation notebook'],
    ['TODAY', 'Run extraction on 100 samples'],
    ['TODAY', 'Export review CSV'],
    ['TOMORROW', 'Manual review (50 samples)'],
    ['DAY 3', 'Manual review (50 samples)'],
    ['DAY 4', 'Run analysis, identify improvements'],
    ['DAY 5', 'Re-run extraction, check if 80%+'],
    ['WEEKEND', 'Update extension code, test edge cases'],
    ['NEXT WEEK', 'Move to session detection']
]
t = Table(action_table, colWidths=[1.2*inch, 4.3*inch])
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#DBEAFE')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 9),
    ('FONTSIZE', (0, 1), (-1, -1), 8),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')])
]))
story.append(t)

story.append(Spacer(1, 0.3*inch))
story.append(Paragraph("Final Advice", heading2_style))
story.append(Paragraph(
    "You're in the <b>research phase</b>, not the <b>shipping phase</b>. "
    "Take time to validate. Iterate until it works. Document everything. "
    "Be willing to pivot. Don't rush to ship. Don't skip validation. "
    "Don't build UI first.",
    body_style
))
story.append(Spacer(1, 0.2*inch))
story.append(Paragraph(
    "<b>The goal:</b> Validate that the core idea works before you invest months "
    "building a product nobody wants.",
    body_style
))

# Build PDF
doc.build(story)
print("✅ Generated: MindCap_Research_Validation_Roadmap.pdf")