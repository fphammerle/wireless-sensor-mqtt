ARG BASE_IMAGE=docker.io/python:3.11-alpine3.20
ARG SOURCE_DIR_PATH=/wireless-sensor-mqtt


# hadolint ignore=DL3006
FROM $BASE_IMAGE as build

RUN apk add --no-cache \
        gcc `# spidev build` \
        git `# setuptools_scm` \
        jq `# edit Pipfile.lock` \
        linux-headers `# spidev build linux/spi/spidev.h` \
        musl-dev `# spidev build` \
    && if [ "$(arch | cut -c1-4)" = "armv" ]; then \
      apk add --no-cache g++ gfortran samurai `# numpy build`; \
    fi \
    && adduser -S build

USER build
RUN pip install --user --no-cache-dir pipenv==2024.1.0

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
# allow manual specification to support build without git history
ARG SETUPTOOLS_SCM_PRETEND_VERSION=
# ctypes.util.find_library fails in python:3.10-alpine3.19
# https://web.archive.org/web/20240213194124/https://github.com/python/cpython/issues/65821
RUN pipenv install --deploy --verbose \
    && pipenv run wireless-sensor-mqtt --help >/dev/null \
    && pipenv graph \
    && pipenv run pip freeze \
    && rm -rf .git/ $PIPENV_CACHE_DIR \
    && sed -i 's#ctypes.util.find_library("gpiod")#"/usr/lib/libgpiod.so.2"#' \
        /wireless-sensor-mqtt/.venv/lib/python*/site-packages/cc1101/_gpio.py \
    && chmod -cR a+rX .

# workaround for broken multi-stage copy
# > failed to copy files: failed to copy directory: Error processing tar file(exit status 1): Container ID ... cannot be mapped to a host ID
USER 0
RUN chown -R 0:0 $SOURCE_DIR_PATH
USER build


# hadolint ignore=DL3006
FROM $BASE_IMAGE

RUN apk add --no-cache \
        ca-certificates \
        libgpiod `# python-cc1101` \
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
