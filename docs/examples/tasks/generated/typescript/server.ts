// GENERATED server stubs: a handler interface + IR-driven registration.
import type * as api from "./api.ts";

export interface TasksHandlers {
  create(title: string): Promise<api.Task>;
  comment(task_id: number, author: User, text: string): Promise<api.Comment>;
  set_state(id: number, state: TaskState): Promise<api.boolean>;
  tasks_subscribe(): unknown;  // Subscription (atom)
  activity_subscribe(): unknown;  // Subscription (log)
}

// Register against the IR (the transport reads kind/params from the contract):
export function register(transport: any, schema: any, h: TasksHandlers): void {
  const bind: Record<string, unknown> = {
    "create": h.create.bind(h),
    "comment": h.comment.bind(h),
    "set_state": h.set_state.bind(h),
    "tasks.subscribe": h.tasks_subscribe.bind(h),
    "activity.subscribe": h.activity_subscribe.bind(h),
  };
  for (const m of schema.services["Tasks"].methods) transport.registerMethod(m, bind[m.name]);
}
