import { ModelOption, SubjectContext } from "@/types";

export const AURORA_API_BASE_URL =
  process.env.NEXT_PUBLIC_AURORA_API_URL || "http://localhost:8000/v1";

export const SUBJECT_OPTIONS: { id: SubjectContext; name: string; description: string; badgeColor: string }[] = [
  {
    id: "AUTO",
    name: "Auto Detect",
    description: "Automatic domain detection based on curriculum context",
    badgeColor: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  },
  {
    id: "DBMS",
    name: "Database Systems",
    description: "SQL, Relational Algebra, Normalization & Transactions",
    badgeColor: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  },
  {
    id: "DSA",
    name: "Data Structures & Algo",
    description: "Trees, Graphs, Sorting, Dynamic Programming",
    badgeColor: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  },
  {
    id: "OOPS",
    name: "Object-Oriented Programming",
    description: "Inheritance, Polymorphism, Design Patterns & Solid",
    badgeColor: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  },
  {
    id: "OS",
    name: "Operating Systems",
    description: "Process Management, Virtual Memory, Deadlocks & Synchronization",
    badgeColor: "bg-rose-500/10 text-rose-400 border-rose-500/20",
  },
  {
    id: "CNT",
    name: "Computer Networks",
    description: "OSI Model, TCP/IP, Routing Algorithms & Network Security",
    badgeColor: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  },
  {
    id: "OOSE",
    name: "Software Engineering",
    description: "UML Diagrams, Agile Methodology, System Requirements",
    badgeColor: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
  },
];

export const MODEL_OPTIONS: ModelOption[] = [
  {
    id: "aurora-unified",
    name: "Samarthan Unified",
    description: "General educational model trained across all CS curricula",
    isDefault: true,
  },
  {
    id: "aurora-dbms",
    name: "Samarthan DBMS",
    description: "Specialized model fine-tuned for Database Systems",
    domain: "DBMS",
  },
  {
    id: "aurora-dsa",
    name: "Samarthan DSA",
    description: "Specialized model fine-tuned for Data Structures & Algorithms",
    domain: "DSA",
  },
  {
    id: "aurora-oops",
    name: "Samarthan OOPs",
    description: "Specialized model fine-tuned for Object Oriented Programming",
    domain: "OOPS",
  },
  {
    id: "aurora-os",
    name: "Samarthan OS",
    description: "Specialized model fine-tuned for Operating Systems",
    domain: "OS",
  },
  {
    id: "aurora-cnt",
    name: "Samarthan Computer Networks",
    description: "Specialized model fine-tuned for Networking Protocols",
    domain: "CNT",
  },
  {
    id: "aurora-oose",
    name: "Samarthan OOSE",
    description: "Specialized model fine-tuned for Software Engineering",
    domain: "OOSE",
  },
];
