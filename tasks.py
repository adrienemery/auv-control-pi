from invoke import task

@task
def dev(ctx):
    ctx.run('docker-compose -f docker-compose-dev.yml up')
