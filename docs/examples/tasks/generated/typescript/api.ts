// GENERATED native TypeScript types — do not edit.

export type TaskState = "open" | "doing" | "done";

export interface User {
  id: number;
  name: string;
}

export interface Comment {
  author: User;
  text: string;
}

export interface Task {
  id: number;
  title: string;
  state: TaskState;
  assignee: User | null;
  comments: Comment[];
}

export interface Event {
  ts: number;
  text: string;
}

