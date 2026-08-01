// Inline 16px stroke icons — no icon dependency.

interface IconProps {
  size?: number;
  className?: string;
}

function Icon({
  size = 16,
  className,
  children,
}: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

/** App glyph: open book. */
export function GlyphIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M8 4.5C6.6 3.5 4.8 3 2.5 3v9c2.3 0 4.1.5 5.5 1.5 1.4-1 3.2-1.5 5.5-1.5V3c-2.3 0-4.1.5-5.5 1.5Z" />
      <path d="M8 4.5v9" />
    </Icon>
  );
}

export function SearchIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="7" cy="7" r="4.25" />
      <path d="m13.5 13.5-3.25-3.25" />
    </Icon>
  );
}

/** Tree / outline view: indented list lines. */
export function TreeIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M2.5 3.5h11" />
      <path d="M5.5 8h8" />
      <path d="M8.5 12.5h5" />
    </Icon>
  );
}

export function CardsIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <rect x="2.5" y="4.5" width="8" height="9" rx="1.5" />
      <path d="M6 2.5h6a1.5 1.5 0 0 1 1.5 1.5v7" />
    </Icon>
  );
}

export function CollapseIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m8.5 4.5-3.5 3.5 3.5 3.5" />
      <path d="m12.5 4.5-3.5 3.5 3.5 3.5" />
    </Icon>
  );
}

export function ExpandIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m7.5 4.5 3.5 3.5-3.5 3.5" />
      <path d="m3.5 4.5 3.5 3.5-3.5 3.5" />
    </Icon>
  );
}

export function ChevronRightIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m6 4 4 4-4 4" />
    </Icon>
  );
}
