/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
import Link from "next/link";
import { EAuthModes } from "@plane/constants";
import { useTranslation } from "@plane/i18n";

interface TermsAndConditionsProps {
  authType?: EAuthModes;
}

const LEGAL_LINKS = {
  "{terms}": "/legal/terms.html",
  "{privacy}": "/legal/privacy.html",
} as const;

function LegalLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="text-secondary" target="_blank" rel="noopener noreferrer">
      <span className="text-13 font-medium underline hover:cursor-pointer">{children}</span>
    </Link>
  );
}

export function TermsAndConditions({ authType = EAuthModes.SIGN_IN }: TermsAndConditionsProps) {
  const { t } = useTranslation();

  // The whole sentence is one translated string rather than fragments joined
  // in a fixed order: Turkish, Japanese and Korean place the verb after both
  // links, so no arrangement of prefix and conjunction suits every language.
  const sentence = t(authType === EAuthModes.SIGN_UP ? "auth.common.terms.signup" : "auth.common.terms.signin");

  const labels: Record<string, string> = {
    "{terms}": t("auth.common.terms.terms_of_service"),
    "{privacy}": t("auth.common.terms.privacy_policy"),
  };

  // Keys are built from the segment plus how many times it has appeared, so
  // they stay stable across re-renders without leaning on the array index.
  const seen = new Map<string, number>();
  const segments = sentence.split(/(\{terms\}|\{privacy\})/).map((part) => {
    const occurrence = (seen.get(part) ?? 0) + 1;
    seen.set(part, occurrence);
    return { part, key: `${part}#${occurrence}` };
  });

  return (
    <div className="flex items-center justify-center">
      <p className="text-center text-13 whitespace-pre-line text-tertiary">
        {segments.map(({ part, key }) => {
          const href = LEGAL_LINKS[part as keyof typeof LEGAL_LINKS];
          if (!href) return <React.Fragment key={key}>{part}</React.Fragment>;
          return (
            <LegalLink key={key} href={href}>
              {labels[part]}
            </LegalLink>
          );
        })}
      </p>
    </div>
  );
}
