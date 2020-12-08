ARG BASE_IMAGE=python:3.8-alpine
ARG SOURCE_DIR_PATH=/wireless-sensor-mqtt


# hadolint ignore=DL3006
FROM $BASE_IMAGE as build

RUN apk add --no-cache \
        gcc `# spidev build` \
        git `# setuptools_scm` \
        jq `# edit Pipfile.lock` \
        linux-headers `# spidev build linux/spi/spidev.h` \
        musl-dev `# spidev build` \
    && adduser -S build

USER build
RUN pip install --user --no-cache-dir pipenv==2020.6.2

ARG SOURCE_DIR_PATH
COPY --chown=build:nobody Pipfile Pipfile.lock $SOURCE_DIR_PATH/
WORKDIR $SOURCE_DIR_PATH
ENV PIPENV_CACHE_DIR=/tmp/pipenv-cache \
    PIPENV_VENV_IN_PROJECT=yes-please \
    PATH=/home/build/.local/bin:$PATH
# `sponge` is not pre-installed
RUN jq 'del(.default."wireless-sensor-mqtt")' Pipfile.lock > Pipfile.lock~ \
    && mv Pipfile.lock~ Pipfile.lock \
    && pipenv install --deploy --verbose
COPY --chown=build:nobody . $SOURCE_DIR_PATH
RUN pipenv install --deploy --verbose \
    && pipenv graph \
    && pipenv run pip freeze \
    && rm -r .git/ $PIPENV_CACHE_DIR

# workaround for broken multi-stage copy
# > failed to copy files: failed to copy directory: Error processing tar file(exit status 1): Container ID ... cannot be mapped to a host ID
USER 0
RUN chown -R 0:0 $SOURCE_DIR_PATH
USER build


# hadolint ignore=DL3006
FROM $BASE_IMAGE

RUN apk add --no-cache \
        ca-certificates \
        tini \
    && find / -xdev -type f -perm /u+s -exec chmod -c u-s {} \; \
    && find / -xdev -type f -perm /g+s -exec chmod -c g-s {} \;

USER nobody

ARG SOURCE_DIR_PATH
COPY --from=build $SOURCE_DIR_PATH $SOURCE_DIR_PATH
ARG VIRTUALENV_PATH=$SOURCE_DIR_PATH/.venv
ENV PATH=$VIRTUALENV_PATH/bin:$PATH
ENTRYPOINT ["tini", "--"]
CMD ["wireless-sensor-mqtt", "--help"]
