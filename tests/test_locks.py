import asyncio
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


async def test_index_lock_pattern():
    execution_lock = asyncio.Lock()
    pending_lock = asyncio.Lock()
    execution_count = 0
    pending_count = 0
    skipped_count = 0

    async def do_task():
        nonlocal execution_count
        nonlocal pending_count
        nonlocal skipped_count
        logger.info("Running task.")

        if pending_lock.locked():
            logger.info("Task already pending. Skipping.")
            skipped_count += 1
            return

        if execution_lock.locked():
            logger.info("Task already executing. Pending.")
            pending_count += 1
            await pending_lock.acquire()

        async with execution_lock:
            logger.info("Executing critical section.")
            # Do some work here
            await asyncio.sleep(0.1)
            execution_count += 1

        if pending_lock.locked():
            pending_lock.release()

        logging.info("Task complete.")

    await asyncio.gather(do_task(), do_task(), do_task())

    assert execution_count == 2
    assert pending_count == 1
    assert skipped_count == 1
