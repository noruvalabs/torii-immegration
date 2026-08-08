"use client";

import { useEffect, useState } from "react";
import { FileText, Loader2, Download } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getDocuments, type Document } from "@/lib/api/cases";

type CaseDocumentsProps = {
  caseId: number;
  token: string;
};

export function CaseDocuments({ caseId, token }: CaseDocumentsProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getDocuments(token, caseId)
      .then((docs) => {
        if (active) setDocuments(docs);
      })
      .catch((e) => {
        if (active) setError(e instanceof Error ? e.message : "Failed to load documents");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [caseId, token]);

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center p-6 text-muted-foreground">
          <Loader2 className="size-5 animate-spin" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-[var(--color-danger)]">
          {error}
        </CardContent>
      </Card>
    );
  }

  if (documents.length === 0) {
    return null; // Don't show the section if there are no documents
  }

  return (
    <Card>
      <CardContent className="p-0">
        <div className="border-b px-6 py-4">
          <h3 className="text-sm font-semibold text-foreground">Attached Documents</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Documents that have been uploaded or attached to this case.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-muted/50 text-xs text-muted-foreground">
              <tr>
                <th className="px-6 py-3 font-medium">Filename</th>
                <th className="px-6 py-3 font-medium">Type</th>
                <th className="px-6 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {documents.map((doc) => (
                <tr key={doc.id} className="hover:bg-muted/30">
                  <td className="px-6 py-3">
                    <div className="flex items-center gap-2">
                      <FileText className="size-4 text-muted-foreground" />
                      <span className="font-medium text-foreground">{doc.filename}</span>
                    </div>
                  </td>
                  <td className="px-6 py-3 text-muted-foreground">
                    {doc.doc_type.replace(/_/g, " ")}
                  </td>
                  <td className="px-6 py-3">
                    {doc.confirmed ? (
                      <Badge tone="success">Confirmed</Badge>
                    ) : (
                      <Badge tone="default">Uploaded</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
