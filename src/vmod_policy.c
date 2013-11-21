#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <sys/socket.h>
#include <netdb.h>

#include "vrt.h"
#include "vsb.h"
#include "bin/varnishd/cache.h"

#include "vcc_if.h"

// such pretty return values.
#define EXIT_OK 0
#define EXIT_NO -1
#define EXIT_ERR 3

int
init_function(struct vmod_priv *priv, const struct VCL_conf *conf)
{
	return (0);
}


int
vmod_check(struct sess *sp, const char *destip, const char *port) {
	char *p, *q;
	int u, v;
	char hdrname[1000];
	int i, hdrnamelen, sock, s;
	struct vsb *meta, *headers;
	struct addrinfo hints, *rp;

	ssize_t len;
	char vpolhdr[] = "VPOL";
	char response[] = "000\0";
	short responsecode;

	AN(destip);
	AN(port);

	meta = VSB_new_auto();
	char foo[] = "x-foo: bar";
	VSB_cat(meta, &foo);

	headers = VSB_new_auto();
	for (u = HTTP_HDR_FIRST; u < sp->http->nhd; u++) {
		q = index(sp->http->hd[u].b, ':');
		if (q == NULL) continue;

		// TODO: fix this buffering
		hdrnamelen = q - sp->http->hd[u].b;
		strncpy(hdrname, sp->http->hd[u].b, hdrnamelen);
		if (u > HTTP_HDR_FIRST)
			VSB_cat(headers, "__");
		VSB_bcat(headers, hdrname, hdrnamelen);
	}
	VSB_finish(meta);
	VSB_finish(headers);

	VSL(SLT_Debug, 0, "headers: (%i) %s ", VSB_len(headers), VSB_data(headers));

	// please, just fix this sockaddr mess for me.
	memset(&hints, 0, sizeof(struct addrinfo));
	hints.ai_family = AF_UNSPEC;
	hints.ai_socktype = SOCK_STREAM;
	hints.ai_flags = AI_NUMERICHOST; // no DNS resolving, must be an IP.

	s = getaddrinfo(destip, port, &hints, &rp);
	if (s != 0) {
		VSL(SLT_VCL_Log, 0, "getaddrinfo(): %i %s", s, gai_strerror(s));
		return EXIT_ERR;
	}
	AN(rp);

	sock = socket(rp->ai_family, rp->ai_socktype, rp->ai_protocol);
	if (sock == -1) {
		VSL(SLT_VCL_Log, 0, "socket(): %i %s", sock, strerror(sock));
		return EXIT_ERR;
	}

	s = connect(sock, rp->ai_addr, rp->ai_addrlen);
	if (s == -1) {
		VSL(SLT_VCL_Log, 0, "connect(): %s", strerror(errno));
		return EXIT_ERR;
	}
	freeaddrinfo(rp);

	// format and send the VPOL header.
	send(sock, &vpolhdr, sizeof(vpolhdr)-1, 0);

	// VSL(SLT_VCL_Log, 0, "meta len is: %i", VSB_len(meta));
	len = htonl(VSB_len(meta));
	send(sock, &len, sizeof(uint32_t), 0);

	len = htonl(VSB_len(headers));
	send(sock, &len, sizeof(uint32_t), 0);

	len = 0; // no body
	send(sock, &len, sizeof(uint32_t), 0);

	// send the content.
	send(sock, VSB_data(meta), VSB_len(meta), 0);
	send(sock, VSB_data(headers), VSB_len(headers), 0);

	// read and parse the response.
	s = recv(sock, &response, sizeof(response), 0);
	if (s == -1) {
		VSL(SLT_VCL_Log, 0, "recv(): %s", strerror(s));
		return EXIT_ERR;
	}

	responsecode = atoi(&response);
	// VSL(SLT_VCL_Log, 0, "responsecode: %i", responsecode);
	if (responsecode == 200) {
		return EXIT_OK;
	}

	return EXIT_NO;
}
