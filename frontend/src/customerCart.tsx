import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ShoppingBag, Trash2 } from "lucide-react";
import { Toast } from "radix-ui";

import { Button } from "./components/ui/Button";
import { Drawer } from "./components/ui/Drawer";
import { QuantityStepper } from "./components/ui/QuantityStepper";
import { ToastNotice, ToastViewport, type ToastMessage } from "./components/ui/ToastNotice";
import {
  customerMediaUrl,
  formatCustomerPrice,
  quoteCustomerCart,
  type CustomerCartLineInput,
  type CustomerCartQuote,
  useCustomerCatalog,
} from "./customerCatalog";

const storageKey = "nosh.customer-cart.v1";
const storageVersion = 1;

type CustomerCartContextValue = {
  addLine: (line: CustomerCartLineInput) => Promise<void>;
  cartCount: number;
  error: string | null;
  isOpen: boolean;
  isUpdating: boolean;
  lines: CustomerCartLineInput[];
  openCart: () => void;
  quote: CustomerCartQuote | null;
  removeLine: (clientLineId: string) => Promise<void>;
  setOpen: (open: boolean) => void;
  updateQuantity: (clientLineId: string, quantity: number) => Promise<void>;
};

const CustomerCartContext = createContext<CustomerCartContextValue | null>(null);

function storedLines(): CustomerCartLineInput[] {
  try {
    const value = JSON.parse(window.localStorage.getItem(storageKey) ?? "null") as {
      lines?: unknown;
      version?: unknown;
    } | null;
    if (value?.version !== storageVersion || !Array.isArray(value.lines)) {
      return [];
    }
    return value.lines.flatMap((line): CustomerCartLineInput[] => {
      if (
        !line || typeof line !== "object" ||
        typeof (line as CustomerCartLineInput).client_line_id !== "string" ||
        typeof (line as CustomerCartLineInput).menu_item_slug !== "string" ||
        !Number.isInteger((line as CustomerCartLineInput).quantity) ||
        !Array.isArray((line as CustomerCartLineInput).option_ids)
      ) {
        return [];
      }
      const candidate = line as CustomerCartLineInput;
      return [{
        client_line_id: candidate.client_line_id.slice(0, 64),
        menu_item_slug: candidate.menu_item_slug,
        note: typeof candidate.note === "string" ? candidate.note.slice(0, 500) || null : null,
        option_ids: [...new Set(candidate.option_ids.filter((optionId) => typeof optionId === "string"))],
        quantity: Math.min(20, Math.max(1, candidate.quantity)),
      }];
    });
  } catch {
    return [];
  }
}

function saveLines(lines: CustomerCartLineInput[]) {
  if (!lines.length) {
    window.localStorage.removeItem(storageKey);
    return;
  }
  window.localStorage.setItem(storageKey, JSON.stringify({ lines, version: storageVersion }));
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "The kitchen could not validate this cart.";
}

export function CustomerCartProvider({ children }: { children: ReactNode }) {
  const [lines, setLines] = useState<CustomerCartLineInput[]>(storedLines);
  const [quote, setQuote] = useState<CustomerCartQuote | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setOpen] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [notice, setNotice] = useState<ToastMessage | null>(null);
  const restoredQuoteAttempted = useRef(false);

  const quoteAndCommit = useCallback(async (
    nextLines: CustomerCartLineInput[],
    successNotice: ToastMessage | null,
  ) => {
    if (!nextLines.length) {
      setLines([]);
      setQuote(null);
      setError(null);
      if (successNotice) {
        setNotice(successNotice);
      }
      return;
    }
    setError(null);
    setIsUpdating(true);
    try {
      const nextQuote = await quoteCustomerCart(nextLines, new AbortController().signal);
      setLines(nextLines);
      setQuote(nextQuote);
      if (successNotice) {
        setNotice(successNotice);
      }
    } catch (requestError) {
      const message = errorMessage(requestError);
      setError(message);
      throw new Error(message);
    } finally {
      setIsUpdating(false);
    }
  }, []);

  useEffect(() => {
    saveLines(lines);
  }, [lines]);

  useEffect(() => {
    if (restoredQuoteAttempted.current || !lines.length) {
      return;
    }
    restoredQuoteAttempted.current = true;
    const controller = new AbortController();
    setIsUpdating(true);
    void quoteCustomerCart(lines, controller.signal)
      .then((nextQuote) => {
        if (!controller.signal.aborted) {
          setQuote(nextQuote);
          setError(null);
        }
      })
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) {
          setError(errorMessage(requestError));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsUpdating(false);
        }
      });
    return () => controller.abort();
  }, [lines]);

  const addLine = useCallback(async (line: CustomerCartLineInput) => {
    await quoteAndCommit([...lines, line], {
      description: `${line.quantity} item${line.quantity === 1 ? "" : "s"} added to your local cart.`,
      title: "Added to cart",
    });
  }, [lines, quoteAndCommit]);

  const updateQuantity = useCallback(async (clientLineId: string, quantity: number) => {
    const nextLines = lines.map((line) => line.client_line_id === clientLineId ? { ...line, quantity } : line);
    await quoteAndCommit(nextLines, {
      description: "Your kitchen total has been checked again.",
      title: "Quantity updated",
    });
  }, [lines, quoteAndCommit]);

  const removeLine = useCallback(async (clientLineId: string) => {
    const nextLines = lines.filter((line) => line.client_line_id !== clientLineId);
    await quoteAndCommit(nextLines, {
      description: nextLines.length ? "Your kitchen total has been updated." : "Your local cart is now empty.",
      title: "Removed from cart",
    });
  }, [lines, quoteAndCommit]);

  const value = useMemo<CustomerCartContextValue>(() => ({
    addLine,
    cartCount: lines.reduce((total, line) => total + line.quantity, 0),
    error,
    isOpen,
    isUpdating,
    lines,
    openCart: () => setOpen(true),
    quote,
    removeLine,
    setOpen,
    updateQuantity,
  }), [addLine, error, isOpen, isUpdating, lines, quote, removeLine, updateQuantity]);

  return (
    <Toast.Provider duration={4500} swipeDirection="right">
      <CustomerCartContext.Provider value={value}>
        {children}
        <ToastNotice notice={notice} onOpenChange={(open) => { if (!open) setNotice(null); }} />
        <ToastViewport />
      </CustomerCartContext.Provider>
    </Toast.Provider>
  );
}

// The hook is intentionally exported with its provider from this module.
// eslint-disable-next-line react-refresh/only-export-components
export function useCustomerCart(): CustomerCartContextValue {
  const value = useContext(CustomerCartContext);
  if (!value) {
    throw new Error("Customer cart components must be rendered within CustomerCartProvider.");
  }
  return value;
}

function ComplementaryDishes({ lines }: { lines: CustomerCartLineInput[] }) {
  const { data: snapshot } = useCustomerCatalog();
  const suggestions = useMemo(() => {
    if (!snapshot || !lines.length) {
      return [];
    }
    const selectedSlugs = new Set(lines.map((line) => line.menu_item_slug));
    const selectedCategories = new Set(
      snapshot.items.filter((item) => selectedSlugs.has(item.slug)).map((item) => item.category.id),
    );
    return snapshot.items
      .filter((item) => item.availability === "available" && !selectedSlugs.has(item.slug))
      .sort(
        (left, right) => Number(!selectedCategories.has(left.category.id)) - Number(!selectedCategories.has(right.category.id)),
      )
      .slice(0, 2);
  }, [lines, snapshot]);

  if (!suggestions.length) {
    return null;
  }
  return (
    <section className="customer-cart-suggestions" aria-labelledby="cart-suggestions-title">
      <p className="eyebrow">Complete the table</p>
      <h3 id="cart-suggestions-title">Pairs well with your choices</h3>
      <ul>
        {suggestions.map((item) => (
          <li key={item.id}>
            <span>{item.name}<small>{formatCustomerPrice(item.final_price_minor, item.currency_code)}</small></span>
            <Link to={"/menu/" + item.slug}>View dish</Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function QuotedCartLine({ line }: { line: CustomerCartQuote["lines"][number] }) {
  const { isUpdating, removeLine, updateQuantity } = useCustomerCart();
  const imageSource = customerMediaUrl(line.media);
  return (
    <article className="customer-cart-line">
      {imageSource ? <img alt={line.media?.alt_text ?? line.name} src={imageSource} /> : null}
      <div className="customer-cart-line-copy">
        <div><h3>{line.name}</h3><strong>{formatCustomerPrice(line.line_total_minor, line.currency_code)}</strong></div>
        {line.selected_options.length ? <ul>{line.selected_options.map((option) => <li key={option.id}>{option.name}{option.price_delta_minor ? ` · +${formatCustomerPrice(option.price_delta_minor, line.currency_code)}` : ""}</li>)}</ul> : <p>Kitchen standard</p>}
        {line.note ? <p className="customer-cart-note">Note: {line.note}</p> : null}
        <footer><QuantityStepper disabled={isUpdating} max={20} value={line.quantity} onValueChange={(quantity) => void updateQuantity(line.client_line_id, quantity)} /><Button aria-label={`Remove ${line.name} from cart`} disabled={isUpdating} size="compact" variant="quiet" onClick={() => void removeLine(line.client_line_id)}><Trash2 aria-hidden="true" /> Remove</Button></footer>
      </div>
    </article>
  );
}

export function CustomerCartDrawer() {
  const { cartCount, error, isOpen, isUpdating, lines, quote, removeLine, setOpen } = useCustomerCart();
  const itemLabel = cartCount === 1 ? "item" : "items";
  return (
    <Drawer
      description={quote ? "Prices and choices are checked with the current kitchen menu." : "Your local selections stay here until the kitchen can check them."}
      footer={quote ? <div className="customer-cart-total"><span>Subtotal</span><strong>{formatCustomerPrice(quote.subtotal_minor, quote.currency_code)}</strong><p>Checkout and order submission begin in the next phase.</p></div> : undefined}
      open={isOpen}
      title={`Your cart · ${cartCount} ${itemLabel}`}
      onOpenChange={setOpen}
    >
      {isUpdating && !quote ? <p aria-live="polite">Checking your saved choices with the kitchen…</p> : null}
      {error ? <section className="customer-cart-error" role="alert"><p>{error}</p><p>Remove the affected dish or return to its page to choose again.</p></section> : null}
      {quote?.lines.map((line) => <QuotedCartLine key={line.client_line_id} line={line} />)}
      {!quote && lines.length ? <ul className="customer-cart-unquoted-lines">{lines.map((line) => <li key={line.client_line_id}><span>{line.menu_item_slug.replaceAll("-", " ")}</span><Button disabled={isUpdating} size="compact" variant="quiet" onClick={() => void removeLine(line.client_line_id)}>Remove</Button></li>)}</ul> : null}
      {!lines.length ? <section className="customer-cart-empty"><ShoppingBag aria-hidden="true" /><h3>Your cart is waiting.</h3><p>Add a dish from today’s menu. Its current price and choices will be checked before it appears here.</p><Link className="nosh-button" data-size="default" data-variant="primary" to="/menu" onClick={() => setOpen(false)}>Browse menu</Link></section> : null}
      {quote ? <ComplementaryDishes lines={lines} /> : null}
    </Drawer>
  );
}
