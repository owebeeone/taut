// GENERATED server handler interface stub.
#pragma once
#include "api.hpp"

struct TasksHandlers {
    virtual Task create(std::string_view title) = 0;
    virtual Comment comment(long long task_id, User author, std::string_view text) = 0;
    virtual bool set_state(long long id, TaskState state) = 0;
    // tasks_subscribe: subscription (atom)
    // activity_subscribe: subscription (log)
};
