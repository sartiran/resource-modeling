FROM centos:7

# Update and install packages
RUN yum -y update
RUN yum -y install epel-release centos-release-scl
RUN yum -y install which gcc python27-tkinter python27-python-devel

# Set environment or python with tkinter
ENV PATH=/opt/rh/python27/root/usr/bin${PATH:+:${PATH}}
ENV LD_LIBRARY_PATH=/opt/rh/python27/root/usr/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
ENV MANPATH=/opt/rh/python27/root/usr/share/man:${MANPATH}
ENV XDG_DATA_DIRS=/opt/rh/python27/root/usr/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}
ENV PKG_CONFIG_PATH=/opt/rh/python27/root/usr/lib64/pkgconfig${PKG_CONFIG_PATH:+:${PKG_CONFIG_PATH}}

# Install required python packages
RUN  pip install matplotlib pandas

# Just a useful entry point
COPY runmodel /runmodel
CMD /runmodel

