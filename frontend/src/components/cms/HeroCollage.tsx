import { useRef, useState } from "react";

import heroCollage from "../../assets/hero-collage.jpg";

export function HeroCollage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  function handlePointerMove(event: React.PointerEvent<HTMLDivElement>) {
    if (
      window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
      window.innerWidth < 1024
    ) {
      return;
    }

    const bounds = containerRef.current?.getBoundingClientRect();
    if (!bounds) return;

    setOffset({
      x: (event.clientX - bounds.left) / bounds.width - 0.5,
      y: (event.clientY - bounds.top) / bounds.height - 0.5,
    });
  }

  const transform = (intensity: number) => ({
    transform: `translate3d(${offset.x * intensity}px, ${offset.y * intensity}px, 0)`,
  });

  return (
    <div
      ref={containerRef}
      className="hero-collage"
      onPointerMove={handlePointerMove}
      onPointerLeave={() => setOffset({ x: 0, y: 0 })}
      aria-hidden="true"
    >
      <div className="hero-collage-powder" style={transform(-14)} />
      <img
        src={heroCollage}
        alt=""
        width={1280}
        height={960}
        style={transform(6)}
      />
      <div className="hero-collage-orb" style={transform(-22)} />
      <div className="hero-collage-rule" style={transform(18)} />
    </div>
  );
}
