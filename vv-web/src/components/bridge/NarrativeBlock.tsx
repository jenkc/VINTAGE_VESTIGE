interface NarrativeBlockProps {
  narrative: string;
}

export default function NarrativeBlock({ narrative }: NarrativeBlockProps) {
  return (
    <p className="font-editorial text-xl italic leading-relaxed text-dark">
      {narrative}
    </p>
  );
}
