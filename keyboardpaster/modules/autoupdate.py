import os
import glob
import warnings
import datetime


# function to self update itself. considering following conditions
#   - the current user can write to this directory
#   - running every run_time_difference seconds to avoid extra runs
#   - avoiding concurrent runs
#   - remote git repo is working.
#   - git command line utility is present in that machine

def self_update():
    """A function to self update a python package's repo."""
    current_repo_dir = os.path.dirname(__file__)
    # add `lastrun.ignore` file in your project's .gitignore so that changes to this file is ignored
    time_status_file = current_repo_dir + "/lastrun.ignore"
    run_time_difference = 600000
    # check if time_status_file file exists. if not try creating it. if unable to create, simply return without updating
    try:
        with open(time_status_file, 'a'):
            os.utime(time_status_file, None)
    except EnvironmentError:
        warnings.warn("WARNING: No WRITE permission on status file. Can not perform update")
        return

    with open(time_status_file, 'r') as status_file_read:
        last_update_run = status_file_read.read().strip()

    if not last_update_run:
        last_update_run = 0
    else:
        last_update_run = int(last_update_run)

    current_time_since_epoch_milliseconds = int((datetime.datetime.utcnow() -
                                                 datetime.datetime(1970, 1, 1)).total_seconds() * 1000)

    # time difference between current run and last run is less than run_time_difference milli seconds, don't run
    if (current_time_since_epoch_milliseconds - last_update_run) < run_time_difference:
        return
    else:
        import fcntl
        import subprocess
        fp = open(time_status_file, 'w')
        try:
            fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            fp.close()
            return
        git_up_cmd = 'cd {0} && git reset --hard HEAD >/dev/null 2>&1 && git clean -f -d >/dev/null 2>&1 ' \
                     '&& git pull >/dev/null 2>&1'.format(current_repo_dir)
        try:
            subprocess.check_output([git_up_cmd], shell=True)
            fp.write(str(current_time_since_epoch_milliseconds))
        except subprocess.CalledProcessError:
            warnings.warn("WARNING: Failed to update repo.")
            pass
        finally:
            fcntl.flock(fp, fcntl.LOCK_UN)
            fp.close()


"""
if 'DISABLE_REPO_AUTO_UPDATE' in os.environ and os.environ['DISABLE_REPO_AUTO_UPDATE'] == '1':
    warnings.warn(
        "WARNING: Self update disabled using environment variable DISABLE_REPO_AUTO_UPDATE")
else:
    __self_update()

modules = glob.glob(os.path.dirname(__file__) + "/*.py")
__all__ = [os.path.basename(f)[:-3] for f in modules if os.path.isfile(f) and not f.startswith('__')]
"""
