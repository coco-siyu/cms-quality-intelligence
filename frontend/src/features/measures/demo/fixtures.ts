import type { DemoMeasure, DemoNewsItem, DemoStatus } from "./types";

export const FICTIONAL_DATA_NOTICE =
  "Fictional prototype data · Not verified CMS guidance · Not for regulatory reporting";

const fixture: [string, string, DemoStatus, string, DemoMeasure["review"], string, string][] = [
  [
    "DM-101",
    "Diabetes: Poor Glycemic Control",
    "modified",
    "Numerator",
    "Approved",
    "Oct 8, 2026",
    "Fictional percentage of patients with diabetes whose latest glycemic assessment indicates poor control.",
  ],
  [
    "HT-102",
    "Controlling High Blood Pressure",
    "modified",
    "Denominator",
    "Approved",
    "Oct 8, 2026",
    "Fictional percentage of patients with hypertension whose blood pressure was controlled during the performance period.",
  ],
  [
    "PV-103",
    "Breast Cancer Screening",
    "modified",
    "Exclusions",
    "Needs re-verification",
    "Sep 22, 2026",
    "Fictional percentage of women ages 50–74 who received a breast cancer screening.",
  ],
  [
    "FU-104",
    "Follow-Up After Emergency Department Visit",
    "added",
    "Measure set",
    "Approved",
    "Oct 12, 2026",
    "Fictional follow-up measure for an emergency department visit involving chronic conditions.",
  ],
  [
    "RD-105",
    "All-Cause Readmission Rate",
    "removed",
    "Measure set",
    "Approved",
    "Oct 5, 2026",
    "Fictional risk-standardized rate of unplanned readmissions after discharge.",
  ],
  [
    "DP-106",
    "Depression Screening and Follow-Up Plan",
    "unchanged",
    "No change",
    "Approved",
    "Oct 3, 2026",
    "Fictional screening measure using a standardized tool and documented follow-up plan.",
  ],
  [
    "FL-107",
    "Falls: Screening for Fall Risk",
    "unchanged",
    "No change",
    "In review",
    "Sep 30, 2026",
    "Fictional screening measure for future fall risk among older adults.",
  ],
  [
    "IM-108",
    "Statin Therapy for Cardiovascular Prevention",
    "unchanged",
    "No change",
    "Approved",
    "Sep 28, 2026",
    "Fictional therapy measure for patients at elevated cardiovascular risk.",
  ],
];

export const demoMeasures: DemoMeasure[] = fixture.map(
  ([id, name, status, field, review, verified, description]) => {
    const specs =
      id === "PV-103"
        ? [
            { name: "Definition", before: description, after: description },
            {
              name: "Numerator",
              before: "Fictional members with a screening during the lookback period.",
              after: "Fictional members with a screening during the lookback period.",
            },
            {
              name: "Denominator",
              before: "Fictional members ages 52–74 enrolled during the performance period.",
              after: "Fictional members ages 52–74 enrolled during the performance period.",
            },
            {
              name: "Exclusions",
              before: "Fictional hospice enrollment. Fictional bilateral procedure history.",
              after: "Fictional hospice or palliative care during the performance period.",
              removed: "Fictional bilateral procedure history.",
              added: "or palliative care",
            },
            {
              name: "Eligibility",
              before: "Fictional patients attributed through a sample assignment methodology.",
              after: "Unavailable in the fictional source. This does not mean it was removed.",
              unavailable: true,
            },
          ]
        : [
            { name: "Definition", before: description, after: description },
            {
              name: "Numerator",
              before:
                id === "DM-101"
                  ? "Fictional patients with a latest HbA1c greater than 9%, or no test recorded."
                  : "Fictional patients meeting the documented outcome or screening criteria.",
              after:
                id === "DM-101"
                  ? "Fictional patients with a latest HbA1c or management indicator greater than 9%, or no test recorded."
                  : "Fictional patients meeting the documented outcome or screening criteria.",
              ...(id === "DM-101" ? { added: "or management indicator" } : {}),
            },
            {
              name: "Denominator",
              before:
                id === "HT-102"
                  ? "Fictional patients ages 18–85 with a hypertension diagnosis."
                  : "Fictional eligible patients with a qualifying encounter.",
              after:
                id === "HT-102"
                  ? "Fictional patients ages 18–85 with a hypertension diagnosis before June 30."
                  : "Fictional eligible patients with a qualifying encounter.",
              ...(id === "HT-102" ? { added: "before June 30" } : {}),
            },
            {
              name: "Exclusions",
              before: "Fictional patients receiving hospice care.",
              after: "Fictional patients receiving hospice care.",
            },
            {
              name: "Eligibility",
              before: "Fictional patients attributed through a sample assignment methodology.",
              after:
                id === "FL-107"
                  ? "Unavailable in the fictional source. This does not mean it was removed."
                  : "Fictional patients attributed through a sample assignment methodology.",
              ...(id === "FL-107" ? { unavailable: true } : {}),
            },
            {
              name: "Calculation logic",
              before: "Fictional numerator divided by eligible denominator, as a percentage.",
              after: "Fictional numerator divided by eligible denominator, as a percentage.",
            },
          ];

    if (status === "added" || status === "removed") {
      specs.unshift({
        name: "Measure set",
        before:
          status === "added"
            ? "Not included in the fictional PY2025 set."
            : "Included in the fictional PY2025 set.",
        after:
          status === "removed"
            ? "Not included in the fictional PY2026 set."
            : "Included in the fictional PY2026 set.",
      });
    }

    return {
      id,
      name,
      status,
      field,
      review,
      verified,
      description,
      specs,
      years: status === "added" ? [2026] : status === "removed" ? [2025] : [2025, 2026],
      unavailable: id === "FL-107",
    };
  },
);

export const demoNews: DemoNewsItem[] = [
  {
    id: "FU-104",
    status: "added",
    title: "New measure added to the PY2026 set",
    body: "A fictional follow-up measure joins the PY2026 prototype list.",
    date: "Oct 12, 2026",
    applies: "PY2026",
  },
  {
    id: "PV-103",
    status: "modified",
    title: "Exclusion language changed for PY2026",
    body: "The fictional exclusion text differs from 2025 and requires re-verification.",
    date: "Sep 22, 2026",
    applies: "PY2026",
  },
  {
    id: "RD-105",
    status: "removed",
    title: "Measure not carried into PY2026",
    body: "The fictional measure appears in the PY2025 prototype set only.",
    date: "Oct 5, 2026",
    applies: "PY2025, final year",
  },
];
