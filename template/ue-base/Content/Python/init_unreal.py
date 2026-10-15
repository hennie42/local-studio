"""Studio startup hook: renders a Movie Render Queue job when the studio broker asks for it.

Only active when STUDIO_RENDER=1 (set by `studio ue-render`); normal editor sessions are untouched.
Uses the PIE executor (same path as the editor UI). Do not use -ExecutePythonScript for this:
in UE 5.8 it quits the editor as soon as the script returns, killing the async render.
"""
import os
import unreal

if os.environ.get("STUDIO_RENDER") == "1":
    _state = {"ticks": 0}

    def _log(msg):
        unreal.log("STUDIO_RENDER " + msg)

    def _object_path(path):
        """/Game/Dir/Asset -> /Game/Dir/Asset.Asset. With a bare package path the render still works,
        but {sequence_name} resolves to "" and frames become hidden files like '.0001.png'."""
        last = path.rsplit("/", 1)[-1]
        return path if "." in last else f"{path}.{last}"

    def _start():
        for key in ("MRQ_SEQUENCE", "MRQ_MAP", "MRQ_CONFIG"):
            os.environ[key] = _object_path(os.environ[key])
        subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
        queue = subsystem.get_queue()
        queue.delete_all_jobs()
        job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
        job.set_editor_property("sequence", unreal.SoftObjectPath(os.environ["MRQ_SEQUENCE"]))
        job.set_editor_property("map", unreal.SoftObjectPath(os.environ["MRQ_MAP"]))
        config = unreal.load_asset(os.environ["MRQ_CONFIG"])
        if config is None:
            _log("error: render config not found: " + os.environ["MRQ_CONFIG"])
            unreal.SystemLibrary.quit_editor()
            return
        job.set_configuration(config)
        executor = unreal.MoviePipelinePIEExecutor(subsystem)
        executor.on_executor_finished_delegate.add_callable_unique(
            lambda ex, ok: (_log("finished success=%s" % ok), unreal.SystemLibrary.quit_editor()))
        executor.on_executor_errored_delegate.add_callable_unique(
            lambda ex, pipe, fatal, text: _log("error fatal=%s %s" % (fatal, text)))
        _state["executor"] = executor  # keep a reference for the whole render
        _log("starting %s %s with %s" % (os.environ["MRQ_MAP"], os.environ["MRQ_SEQUENCE"], os.environ["MRQ_CONFIG"]))
        subsystem.render_queue_with_executor_instance(executor)

    def _tick(delta):
        _state["ticks"] += 1
        if _state["ticks"] < 120:  # let the editor finish loading
            return
        unreal.unregister_slate_post_tick_callback(_state["handle"])
        try:
            _start()
        except Exception as e:
            _log("error: %s" % e)
            unreal.SystemLibrary.quit_editor()

    _state["handle"] = unreal.register_slate_post_tick_callback(_tick)
