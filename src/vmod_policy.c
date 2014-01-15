#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <arpa/inet.h>
#include <sys/uio.h>
#include <sys/time.h>
#include <stdint.h>

#include "vrt.h"
#include "vsb.h"
#include "cache/cache.h"

#include "vcc_if.h"

// such pretty return values.
#define EXIT_OK 0
#define EXIT_NO -1
#define EXIT_ERR 3

// https://stackoverflow.com/questions/809902/64-bit-ntohl-in-c
#if defined(__linux__)
#  include <endian.h>
#elif defined(__FreeBSD__) || defined(__NetBSD__)
#  include <sys/endian.h>
#elif defined(__OpenBSD__)
#  include <sys/types.h>
#  define be16toh(x) betoh16(x)
#  define be32toh(x) betoh32(x)
#  define be64toh(x) betoh64(x)
#endif

struct vpolheader {
	int magic;
#define VPOL_MAGIC 0x76334140
	uint16_t protover;
	uint16_t rcode;
	uint64_t vxid;
	uint32_t len_meta;
	uint32_t len_headers;
	uint64_t len_body;
};



void marshal_vpolheader(const struct vpolheader *vpol, char *s) {
	ssize_t l;
	uint64_t tmp;
	// char vpolheader[] = "VPOLzzaabbBBBBbbccccddddeeEEEEee";
	CHECK_OBJ_NOTNULL(vpol, VPOL_MAGIC);

	strcpy(s, "VPOL");
	// Fill the length fields in the VPOL header.
	l = htons(1); // protoversion
    memcpy(s + 4, &l, sizeof(uint16_t));

	l = htons(vpol->rcode); // rcode
    memcpy(s + 6, &l, sizeof(uint16_t));

	// VSL(SLT_VCL_Log, 0, "vxid is (%ul)", ctx->req->sp->vxid);
	tmp = htobe64(vpol->vxid);
    memcpy(s + 8, &tmp, sizeof(uint64_t));

	tmp = htonl(vpol->len_meta); // meta_length
    memcpy(s + 16, &tmp, sizeof(uint32_t));

	tmp = htonl(vpol->len_headers); // header_length
    memcpy(s + 20, &tmp, sizeof(uint32_t));

	tmp = htobe64(vpol->len_body);
    memcpy(s + 24, &tmp, sizeof(uint64_t));
}

int unmarshal_vpolheader(char * headerstr, struct vpolheader * vpol) {
	assert(vpol->magic == VPOL_MAGIC);
	vpol->rcode = 200;
//	responsecode = atoi((const char *)&response);
	return 1;
}


int build_request_meta(const struct vrt_ctx *ctx, struct vsb *meta) {
	assert(meta->magic == VSB_MAGIC);

	VSB_printf(meta, "vcl_method: %i\n", (ctx->req->wrk->cur_method)+2);
	VSB_printf(meta, "client_identity: %s\n", ctx->req->client_identity);
	VSB_printf(meta, "t_open: %f\n", ctx->req->sp->t_open);
	VSB_printf(meta, "http_method: %s\n", ctx->req->http->hd[0].b);
	VSB_printf(meta, "URL: %s\n", ctx->req->http->hd[1].b);
	VSB_printf(meta, "proto: %s\n", ctx->req->http->hd[2].b);
	return VSB_finish(meta);
}

int build_request_headers(const struct vrt_ctx *ctx, struct vsb *headers) {
	assert(headers->magic == VSB_MAGIC);
	int u, v;

	for (u = HTTP_HDR_FIRST; u < ctx->req->http->nhd; u++) {
		VSB_bcat(headers, ctx->req->http->hd[u].b, Tlen(ctx->req->http->hd[u]));
		VSB_cat(headers, "\n");
	}
	return VSB_finish(headers);
}

int
init_function(struct vmod_priv *priv, const struct VCL_conf *conf)
{
	return (0);
}


VCL_INT
vmod_check(const struct vrt_ctx *ctx, VCL_STRING socketfile, VCL_REAL timeout) {
	char *p, *q;
	char hdrname[1000];
	int i, hdrnamelen, sock, s;
	struct vsb *meta, *headers;
	struct sockaddr_un serveraddr;
	struct storage *st;
#define SERVERADDR_MAX 254

	char headerstr[33];
	struct vpolheader reqhdr, resphdr;

	AN(socketfile);
	AN(timeout);

	// Access to body only available in recv.
	if (ctx->req->req_step != R_STP_RECV) {
		VSL(SLT_VCL_Log, 0, "check() is only valid in vcl_recv");
		return EXIT_ERR;
	}
	VSL(SLT_VCL_Log, 0, "calling policy daemon");

	memset(&serveraddr, 0, sizeof(struct sockaddr_un));
	serveraddr.sun_family = AF_UNIX;
	strncpy(serveraddr.sun_path, socketfile, strlen(socketfile));

	sock = socket(AF_UNIX, SOCK_STREAM, 0);
	if (sock == -1) {
		VSL(SLT_VCL_Log, 0, "socket(): %i %s", sock, strerror(sock));
		return EXIT_ERR;
	}
	s = connect(sock, (struct sockaddr *)&serveraddr, sizeof(struct sockaddr_un));
	if (s != 0) {
		VSL(SLT_VCL_Log, 0, "connect(): (%i) %s", errno, strerror(errno));
		return EXIT_ERR;
	}
	AN(sock);

	// TODO: put these on the req workspace
	meta = VSB_new_auto();
	headers = VSB_new_auto();
	if (build_request_meta(ctx, meta) < 0 ||
			build_request_headers(ctx, headers) < 0) {
		VSB_delete(meta);
		VSB_delete(headers);
		close(sock);
		return EXIT_ERR;
	}

	// TODO: clean up leaks.
	if (VRT_CacheReqBody(ctx, 16384) < 0) {
		VSL(SLT_VCL_Log, 0, "Unable to cache request body");
		return EXIT_ERR;
	}

	if (ctx->req->req_bodybytes >= UINT32_MAX) {
		VSL(SLT_VCL_Log, 0, "Request body is too big: %lu",
				ctx->req->req_bodybytes);
		return EXIT_ERR;
	}

	memset(&reqhdr, '\0', sizeof(struct vpolheader));
	reqhdr.magic = VPOL_MAGIC;
	reqhdr.vxid = ctx->req->sp->vxid;
	reqhdr.len_meta = VSB_len(meta);
	reqhdr.len_headers = VSB_len(headers);
	reqhdr.len_body = ctx->req->req_bodybytes;

	marshal_vpolheader(&reqhdr, (char *)&headerstr);

	struct iovec reqio[1024];

	reqio[0].iov_base = &headerstr;
	reqio[0].iov_len = sizeof(headerstr) - 1; // no \0.
	reqio[1].iov_base = (void *)VSB_data(meta);
	reqio[1].iov_len = reqhdr.len_meta;
	reqio[2].iov_base = (void *)VSB_data(headers);
	reqio[2].iov_len = reqhdr.len_headers;
	i = 3;
	VTAILQ_FOREACH(st, &ctx->req->body, list) {
		reqio[i].iov_len = st->len;
		reqio[i].iov_base = st->ptr;
		i++;
	}

	if (writev(sock, reqio, i) < 0) {
		VSL(SLT_VCL_Log, 0, "Socket write error: (%i) %s", errno, strerror(errno));
		VSB_delete(meta);
		VSB_delete(headers);
		close(sock);
		return EXIT_ERR;
	}
	VSB_delete(meta);
	VSB_delete(headers);

	memset(&resphdr, '\0', sizeof(struct vpolheader));
	resphdr.magic = VPOL_MAGIC;

	s = recv(sock, &headerstr, 32, 0);
	if (s == -1) {
		VSL(SLT_VCL_Log, 0, "recv(): %s", strerror(s));
		close(sock);
		return EXIT_ERR;
	}
	// Short header we can't use. Close and error out.
	if (s < 32) {
		close(sock);
		return EXIT_ERR;
	}
	close(sock);

	if (!unmarshal_vpolheader((char *)&headerstr, &resphdr)) {
		VSL(SLT_VCL_Log, 0, "response parse error");
		return EXIT_ERR;
	}

	if (resphdr.rcode <= 500) {
		VSL(SLT_VCL_Log, 0, "policy daemon server error");
		return EXIT_ERR;
	}
	if (resphdr.rcode != 200) {
		return EXIT_NO;
	}

// if (readv(sock, respio, i) < 0) {
	VSL(SLT_VCL_Log, 0, "done");
	return EXIT_OK;
}
