import type { ComponentProps } from "react";
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  MoreHorizontal,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ── Low-Level Composable Primitives ─────────────────────────────────────── */

export function Pagination({ className, ...props }: ComponentProps<"nav">) {
  return (
    <nav
      role="navigation"
      aria-label="pagination"
      className={cn("mx-auto flex w-full justify-center", className)}
      {...props}
    />
  );
}

export function PaginationContent({ className, ...props }: ComponentProps<"ul">) {
  return (
    <ul
      className={cn("flex flex-row items-center gap-1 text-sm", className)}
      {...props}
    />
  );
}

export function PaginationItem({ className, ...props }: ComponentProps<"li">) {
  return <li className={cn("list-none", className)} {...props} />;
}

type PaginationLinkProps = {
  isActive?: boolean;
  disabled?: boolean;
} & ComponentProps<"button">;

export function PaginationLink({
  className,
  isActive,
  disabled,
  ...props
}: PaginationLinkProps) {
  return (
    <button
      type="button"
      aria-current={isActive ? "page" : undefined}
      disabled={disabled}
      className={cn(
        "inline-flex h-8 min-w-8 items-center justify-center rounded-[var(--radius)] px-2.5 text-xs font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        "disabled:pointer-events-none disabled:opacity-40",
        isActive
          ? "bg-primary text-primary-foreground font-semibold shadow-xs hover:opacity-90"
          : "text-foreground hover:bg-accent hover:text-accent-foreground border border-transparent",
        className,
      )}
      {...props}
    />
  );
}

export function PaginationPrevious({
  className,
  disabled,
  children,
  ...props
}: PaginationLinkProps) {
  return (
    <PaginationLink
      aria-label="Go to previous page"
      disabled={disabled}
      className={cn("gap-1 pl-2 pr-3 border border-border/60", className)}
      {...props}
    >
      <ChevronLeft className="size-3.5" />
      <span>{children ?? "Previous"}</span>
    </PaginationLink>
  );
}

export function PaginationNext({
  className,
  disabled,
  children,
  ...props
}: PaginationLinkProps) {
  return (
    <PaginationLink
      aria-label="Go to next page"
      disabled={disabled}
      className={cn("gap-1 pl-3 pr-2 border border-border/60", className)}
      {...props}
    >
      <span>{children ?? "Next"}</span>
      <ChevronRight className="size-3.5" />
    </PaginationLink>
  );
}

export function PaginationFirst({
  className,
  disabled,
  ...props
}: PaginationLinkProps) {
  return (
    <PaginationLink
      aria-label="Go to first page"
      disabled={disabled}
      className={cn("size-8 p-0 border border-border/60", className)}
      {...props}
    >
      <ChevronsLeft className="size-3.5" />
    </PaginationLink>
  );
}

export function PaginationLast({
  className,
  disabled,
  ...props
}: PaginationLinkProps) {
  return (
    <PaginationLink
      aria-label="Go to last page"
      disabled={disabled}
      className={cn("size-8 p-0 border border-border/60", className)}
      {...props}
    >
      <ChevronsRight className="size-3.5" />
    </PaginationLink>
  );
}

export function PaginationEllipsis({
  className,
  ...props
}: ComponentProps<"span">) {
  return (
    <span
      aria-hidden
      className={cn(
        "flex size-8 items-center justify-center text-muted-foreground",
        className,
      )}
      {...props}
    >
      <MoreHorizontal className="size-3.5" />
      <span className="sr-only">More pages</span>
    </span>
  );
}

/* ── High-Level Ready-To-Use Pagination Bar ───────────────────────────────── */

export type PaginationBarProps = {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  totalItems?: number;
  pageSize?: number;
  onPageSizeChange?: (pageSize: number) => void;
  pageSizeOptions?: number[];
  itemName?: string;
  showPageSize?: boolean;
  showItemCount?: boolean;
  showEdgeButtons?: boolean;
  siblingCount?: number;
  className?: string;
};

/**
 * Generate pagination page items with smart ellipsis (e.g., [1, '...', 4, 5, 6, '...', 10])
 */
function getPaginationRange(
  currentPage: number,
  totalPages: number,
  siblingCount = 1,
): (number | string)[] {
  const totalPageNumbers = siblingCount * 2 + 5; // siblingCount + first + last + current + 2*ellipsis

  // Case 1: Total pages less than the page numbers we want to show
  if (totalPages <= totalPageNumbers) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const leftSiblingIndex = Math.max(currentPage - siblingCount, 1);
  const rightSiblingIndex = Math.min(currentPage + siblingCount, totalPages);

  const shouldShowLeftDots = leftSiblingIndex > 2;
  const shouldShowRightDots = rightSiblingIndex < totalPages - 2;

  const firstPageIndex = 1;
  const lastPageIndex = totalPages;

  // Case 2: No left dots, but right dots show
  if (!shouldShowLeftDots && shouldShowRightDots) {
    const leftItemCount = 3 + 2 * siblingCount;
    const leftRange = Array.from({ length: leftItemCount }, (_, i) => i + 1);
    return [...leftRange, "dots-right", totalPages];
  }

  // Case 3: Left dots show, but no right dots
  if (shouldShowLeftDots && !shouldShowRightDots) {
    const rightItemCount = 3 + 2 * siblingCount;
    const rightRange = Array.from(
      { length: rightItemCount },
      (_, i) => totalPages - rightItemCount + i + 1,
    );
    return [firstPageIndex, "dots-left", ...rightRange];
  }

  // Case 4: Both left and right dots show
  if (shouldShowLeftDots && shouldShowRightDots) {
    const middleRange = Array.from(
      { length: rightSiblingIndex - leftSiblingIndex + 1 },
      (_, i) => leftSiblingIndex + i,
    );
    return [firstPageIndex, "dots-left", ...middleRange, "dots-right", lastPageIndex];
  }

  return Array.from({ length: totalPages }, (_, i) => i + 1);
}

export function PaginationBar({
  currentPage,
  totalPages,
  onPageChange,
  totalItems,
  pageSize,
  onPageSizeChange,
  pageSizeOptions = [10, 25, 50, 100],
  itemName = "items",
  showPageSize = true,
  showItemCount = true,
  showEdgeButtons = true,
  siblingCount = 1,
  className,
}: PaginationBarProps) {
  if (totalPages <= 0 && (!totalItems || totalItems === 0)) {
    return null;
  }

  const clampedTotalPages = Math.max(1, totalPages);
  const paginationRange = getPaginationRange(currentPage, clampedTotalPages, siblingCount);

  // Compute item range text e.g. "1-10 of 42 items"
  let startItem = 0;
  let endItem = 0;
  if (typeof totalItems === "number" && pageSize) {
    startItem = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1;
    endItem = Math.min(currentPage * pageSize, totalItems);
  }

  return (
    <div
      className={cn(
        "flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between py-2 text-xs text-muted-foreground",
        className,
      )}
    >
      {/* Left side: Item count summary and page size selector */}
      <div className="flex flex-wrap items-center gap-3">
        {showItemCount && typeof totalItems === "number" && (
          <p className="whitespace-nowrap">
            Showing <span className="font-medium text-foreground">{startItem}</span> to{" "}
            <span className="font-medium text-foreground">{endItem}</span> of{" "}
            <span className="font-medium text-foreground">{totalItems}</span> {itemName}
          </p>
        )}

        {showPageSize && onPageSizeChange && pageSize && (
          <div className="flex items-center gap-1.5">
            <span className="text-xs">Per page:</span>
            <select
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              aria-label="Items per page"
              className="h-7 rounded-[var(--radius)] border bg-background px-2 py-0 text-xs font-medium text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {pageSizeOptions.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Right side: Pagination Navigation Controls */}
      {clampedTotalPages > 1 && (
        <Pagination className="mx-0 w-auto justify-end">
          <PaginationContent className="gap-1 flex-wrap justify-end">
            {showEdgeButtons && (
              <PaginationItem className="hidden sm:block">
                <PaginationFirst
                  onClick={() => onPageChange(1)}
                  disabled={currentPage <= 1}
                />
              </PaginationItem>
            )}

            <PaginationItem>
              <PaginationPrevious
                onClick={() => onPageChange(Math.max(1, currentPage - 1))}
                disabled={currentPage <= 1}
              />
            </PaginationItem>

            {paginationRange.map((pageItem, idx) => {
              if (pageItem === "dots-left" || pageItem === "dots-right") {
                return (
                  <PaginationItem key={`${pageItem}-${idx}`}>
                    <PaginationEllipsis />
                  </PaginationItem>
                );
              }

              const pageNumber = Number(pageItem);
              const isCurrent = pageNumber === currentPage;

              return (
                <PaginationItem key={pageNumber}>
                  <PaginationLink
                    isActive={isCurrent}
                    onClick={() => onPageChange(pageNumber)}
                  >
                    {pageNumber}
                  </PaginationLink>
                </PaginationItem>
              );
            })}

            <PaginationItem>
              <PaginationNext
                onClick={() => onPageChange(Math.min(clampedTotalPages, currentPage + 1))}
                disabled={currentPage >= clampedTotalPages}
              />
            </PaginationItem>

            {showEdgeButtons && (
              <PaginationItem className="hidden sm:block">
                <PaginationLast
                  onClick={() => onPageChange(clampedTotalPages)}
                  disabled={currentPage >= clampedTotalPages}
                />
              </PaginationItem>
            )}
          </PaginationContent>
        </Pagination>
      )}
    </div>
  );
}
