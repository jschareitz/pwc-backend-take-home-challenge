from uuid import UUID


class JobNotFoundException(Exception):
    def __init__(self, job_id: UUID):
        self.message = f"Job with id {job_id} not found"
        super().__init__(self.message)


class JobAlreadyStartedException(Exception):
    def __init__(self, job_id: UUID):
        self.message = f"Job with id {job_id} can't be deleted, because it has already started, failed or finished"
        super().__init__(self.message)
