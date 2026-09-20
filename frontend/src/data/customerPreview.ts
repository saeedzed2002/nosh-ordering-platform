import heroImage from "../assets/nosh-hero-food.webp";
import seasonalSpreadImage from "../assets/nosh-seasonal-spread.webp";
import type { StatusTone } from "../components/ui/StatusBadge";

export type MenuPreviewCategory = {
  id: "all" | "bowls" | "flatbreads" | "small-plates" | "sweets";
  label: string;
  note: string;
};

export type MenuPreviewDish = {
  alt: string;
  category: Exclude<MenuPreviewCategory["id"], "all">;
  description: string;
  id: string;
  image: string;
  name: string;
  priceCents: number;
  status: StatusTone;
  tags: string[];
};

export const menuPreviewCategories: MenuPreviewCategory[] = [
  { id: "all", label: "Everything", note: "Today’s short list" },
  { id: "bowls", label: "Bowls", note: "Built around the grill" },
  { id: "flatbreads", label: "Flatbreads", note: "Torn, shared, repeated" },
  { id: "small-plates", label: "Small plates", note: "Bright things for the table" },
  { id: "sweets", label: "Sweets", note: "A gentle finish" },
];

export const menuPreviewDishes: MenuPreviewDish[] = [
  {
    id: "harissa-chicken-bowl",
    category: "bowls",
    name: "Harissa chicken bowl",
    description: "Charred chicken, hummus, cucumber, chickpeas, and pickled onion.",
    priceCents: 1450,
    status: "available",
    tags: ["Gluten-aware", "Spicy"],
    image: heroImage,
    alt: "Grilled chicken with hummus, chickpeas, cucumber, herbs, and flatbread",
  },
  {
    id: "market-flatbread",
    category: "flatbreads",
    name: "Market flatbread",
    description: "Fire-kissed vegetables, feta, herb oil, and a quietly blistered crust.",
    priceCents: 1250,
    status: "available",
    tags: ["Vegetarian", "Shareable"],
    image: seasonalSpreadImage,
    alt: "Vegetable flatbread with feta, herbs, and roasted peppers on a cream table",
  },
  {
    id: "citrus-salad",
    category: "small-plates",
    name: "Citrus and fennel",
    description: "Blood orange, shaved fennel, pistachio, and soft herbs with olive oil.",
    priceCents: 850,
    status: "available",
    tags: ["Vegan", "Bright"],
    image: seasonalSpreadImage,
    alt: "Citrus and fennel salad with herbs and pistachios in a ceramic bowl",
  },
  {
    id: "olive-oil-cake",
    category: "sweets",
    name: "Olive oil cake",
    description: "Citrus olive oil cake with labneh cream and a pinch of sea salt.",
    priceCents: 650,
    status: "unavailable",
    tags: ["Seasonal", "Limited"],
    image: seasonalSpreadImage,
    alt: "A warm cream table set with grilled citrus and an olive branch",
  },
];

export const kitchenMoments = [
  { time: "09:00", label: "Prep starts with the market" },
  { time: "12:00", label: "First pickup leaves the pass" },
  { time: "18:00", label: "Last delivery heads across town" },
];

export const customerBenefits = [
  {
    title: "Cooked for the handoff",
    copy: "A short menu lets the kitchen make each dish close to the moment it leaves.",
  },
  {
    title: "A clear way home",
    copy: "Pickup and delivery are stated early, so the next decision is never hidden.",
  },
  {
    title: "Seasonal by design",
    copy: "The menu shifts with what is good now instead of pretending every dish is permanent.",
  },
];
