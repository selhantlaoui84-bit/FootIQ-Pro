type InfoTooltipProps = {
  label?: string;
  content: string;
};

export function InfoTooltip({ label = 'Aide', content }: InfoTooltipProps) {
  return (
    <span className="tooltip">
      <button className="tooltipTrigger" type="button" aria-label={`${label}: ${content}`}>
        ?
      </button>
      <span className="tooltipBubble" role="tooltip">
        {content}
      </span>
    </span>
  );
}

