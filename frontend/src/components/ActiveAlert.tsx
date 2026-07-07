import type { ReactNode } from "react";

interface ActiveAlertProps {
  icon: ReactNode;
}

export function ActiveAlert({ icon }: ActiveAlertProps) {
  return (
    <section className="panel">
      <h2>{icon} Active Alert</h2>
      <p>No confirmed FOD alert is active.</p>
    </section>
  );
}
