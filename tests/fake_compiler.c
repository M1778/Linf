#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <io.h>
#include <fcntl.h>
#endif

static void json_string(FILE *out, const char *text) {
    fputc('"', out);
    for (const unsigned char *p = (const unsigned char *)text; *p; ++p) {
        if (*p == '"' || *p == '\\') {
            fputc('\\', out);
            fputc(*p, out);
        } else if (*p < 32) {
            fprintf(out, "\\u%04x", *p);
        } else {
            fputc(*p, out);
        }
    }
    fputc('"', out);
}

int main(int argc, char **argv) {
    if (argc != 4 || strcmp(argv[2], "--diagnostics=json") ||
        strcmp(argv[3], "--color=never")) return 97;
    const char *log_path = getenv("LINF_ARGV_LOG");
    if (log_path) {
        FILE *log = fopen(log_path, "wb");
        if (!log) return 96;
        fputc('[', log);
        for (int i = 1; i < argc; ++i) {
            if (i != 1) fputc(',', log);
            json_string(log, argv[i]);
        }
        fputc(']', log);
        if (fclose(log)) return 96;
    }
    size_t size = strlen(argv[1]) + 8;
    char *path = malloc(size);
    if (!path) return 95;
    snprintf(path, size, "%s.jsonl", argv[1]);
    FILE *input = fopen(path, "rb");
    if (!input) { free(path); return 94; }
    FILE *output = getenv("LINF_FAKE_STDOUT") ? stdout : stderr;
#ifdef _WIN32
    _setmode(_fileno(output), _O_BINARY);
#endif
    char buffer[8192];
    size_t got;
    while ((got = fread(buffer, 1, sizeof(buffer), input)) != 0) {
        if (fwrite(buffer, 1, got, output) != got) return 93;
    }
    if (ferror(input)) return 92;
    fclose(input);
    snprintf(path, size, "%s.rc", argv[1]);
    input = fopen(path, "rb");
    int result = 0;
    if (input) {
        if (fscanf(input, "%d", &result) != 1) result = 91;
        fclose(input);
    }
    free(path);
    return result;
}
