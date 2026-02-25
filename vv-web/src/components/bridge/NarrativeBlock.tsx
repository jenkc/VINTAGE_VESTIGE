interface NarrativeBlockProps {
  narrative: string;
}

export default function NarrativeBlock({ narrative }: NarrativeBlockProps) {
  return (
    <blockquote className="rounded-sm border-l-[3px] border-gold bg-cream px-4 py-3">
      <p className="font-serif text-[13px] italic leading-relaxed text-charcoal-soft">
        {narrative}
      </p>
    </blockquote>
  );
}
