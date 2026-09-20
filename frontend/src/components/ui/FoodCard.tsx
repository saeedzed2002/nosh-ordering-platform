import { ArrowUpRight } from "lucide-react";

import { Button } from "./Button";
import { StatusBadge, type StatusTone } from "./StatusBadge";

type FoodCardProps = {
  actionLabel?: string;
  alt: string;
  description: string;
  image: string;
  name: string;
  onAction?: () => void;
  price: string;
  status?: StatusTone;
  tags?: string[];
};

export function FoodCard({
  actionLabel,
  alt,
  description,
  image,
  name,
  onAction,
  price,
  status = "available",
  tags = [],
}: FoodCardProps) {
  const canOrder = status === "available";

  return (
    <article className="nosh-food-card">
      <img src={image} alt={alt} />
      <div className="nosh-food-card-content">
        <div className="nosh-food-card-heading">
          <h3>{name}</h3>
          <strong>{price}</strong>
        </div>
        <p>{description}</p>
        <div className="nosh-food-card-meta">
          {tags.map((tag) => (
            <span key={tag} className="nosh-tag">{tag}</span>
          ))}
          <StatusBadge tone={status}>
            {canOrder ? "Available" : "Unavailable"}
          </StatusBadge>
        </div>
        <Button disabled={!canOrder} variant="secondary" onClick={onAction}>
          {actionLabel ?? (canOrder ? "View dish" : "Unavailable")} <ArrowUpRight aria-hidden="true" />
        </Button>
      </div>
    </article>
  );
}
