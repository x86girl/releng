FROM registry.fedoraproject.org/fedora:38
LABEL name="rdo-toolbox"

COPY container/extra-packages /extra-packages
RUN dnf -y install $(<extra-packages) && dnf clean all
RUN rm /extra-packages

COPY container/requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
RUN rm /requirements.txt

COPY container/etc /etc/
COPY container/etc/profile.d /etc/profile.d

COPY . /releng
RUN pip install /releng
