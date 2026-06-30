FROM ubuntu:22.04

ARG BOOST_VERSION=1.82.0
ARG BOOST_UNDERSCORE=1_82_0
ARG BOOST_TARBALL_SHA256=a6e1ab9b0860e6a2881dd7b21fe9f737a095e5f33a3a874afc6a345228597ee6

ENV PIP_NO_CACHE_DIR=1 \
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		bzip2 \
		build-essential \
		ca-certificates \
		wget \
		python3 \
		python3.10-dev \
		python3-pip \
		python3-venv \
		python-is-python3 \
	&& rm -rf /var/lib/apt/lists/*

RUN wget -q -O /tmp/boost.tar.bz2 \
		"https://archives.boost.io/release/${BOOST_VERSION}/source/boost_${BOOST_UNDERSCORE}.tar.bz2" \
	&& echo "${BOOST_TARBALL_SHA256}  /tmp/boost.tar.bz2" | sha256sum -c - \
	&& mkdir -p /tmp/boost \
	&& tar -xjf /tmp/boost.tar.bz2 -C /tmp/boost --strip-components=1 \
	&& cd /tmp/boost \
	&& ./bootstrap.sh --with-libraries=python --with-python=python3 \
	&& ./b2 -j2 --with-python variant=release link=shared runtime-link=shared install \
	&& ldconfig \
	&& rm -rf /tmp/boost /tmp/boost.tar.bz2

RUN python -m pip install --upgrade pip \
	&& python -m pip install \
		pymimir==0.9.62 \
		lab==8.1 \
		pynauty==2.8.6 \
		graphviz==0.20.1 \
		dlplan==0.3.29 \
		clingo \
		jsonpickle \
		termcolor \
		numpy \
		psutil \
		intbitset \
		bloom-filter2 \
		tqdm \
		tarski
