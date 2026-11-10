"use client";

import type { ReactTable, RowData, TableFeatures } from "@tanstack/react-table";
import type { ReactNode } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

/** Renders a TanStack table with the app's table styles; `columnClassName` styles a column. */
export function DataTable<TFeatures extends TableFeatures, TData extends RowData>({
  table,
  empty,
  columnClassName = {},
}: {
  table: ReactTable<TFeatures, TData>;
  empty: ReactNode;
  columnClassName?: Record<string, string>;
}) {
  const rows = table.getRowModel().rows;
  const columnCount = table.getAllLeafColumns().length;
  return (
    <Table>
      <TableHeader>
        {table.getHeaderGroups().map((group) => (
          <TableRow key={group.id}>
            {group.headers.map((header) => (
              <TableHead key={header.id} className={columnClassName[header.column.id]}>
                {header.isPlaceholder ? null : <table.FlexRender header={header} />}
              </TableHead>
            ))}
          </TableRow>
        ))}
      </TableHeader>
      <TableBody>
        {rows.length === 0 ? (
          <TableRow>
            <TableCell colSpan={columnCount} className="py-12 text-center text-on-surface-variant">
              {empty}
            </TableCell>
          </TableRow>
        ) : (
          rows.map((row) => (
            <TableRow key={row.id}>
              {row.getAllCells().map((cell) => (
                <TableCell key={cell.id} className={cn(columnClassName[cell.column.id])}>
                  <table.FlexRender cell={cell} />
                </TableCell>
              ))}
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}
