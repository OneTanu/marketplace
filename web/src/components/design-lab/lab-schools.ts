// Lab-only schools, so palettes can be compared before a school joins. Real schools keep their
// colors in the database (School.colors). Hex values are approximate; take exact ones from each
// school's brand guide before adding a school.
export type LabSchool = {
  slug: string;
  name: string;
  shortName: string;
  colors: string[];
};

export const LAB_SCHOOLS: LabSchool[] = [
  { slug: "umd", name: "University of Maryland", shortName: "UMD", colors: ["#E21833", "#FFD200", "#000000"] },
  { slug: "towson", name: "Towson University", shortName: "Towson", colors: ["#FFBB00", "#000000"] },
  { slug: "umbc", name: "UMBC", shortName: "UMBC", colors: ["#000000", "#FDB515"] },
  { slug: "morgan", name: "Morgan State University", shortName: "Morgan", colors: ["#0A2D6E", "#F47B20"] },
];

export function labSchool(slug: string) {
  return LAB_SCHOOLS.find((school) => school.slug === slug) ?? LAB_SCHOOLS[0];
}
