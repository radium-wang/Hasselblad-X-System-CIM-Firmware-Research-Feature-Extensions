#ifndef X2D2_DIGITAL_ZOOM_H
#define X2D2_DIGITAL_ZOOM_H

#ifdef __cplusplus
extern "C" {
#endif

typedef struct DzSensor {
    int width_px;
    int height_px;
    double width_mm;
    double height_mm;
    int cfa_quad;
} DzSensor;

typedef struct DzWindow {
    int x;
    int y;
    int width;
    int height;
} DzWindow;

enum DzStatus {
    DZ_OK = 0,
    DZ_INVALID_ARGUMENT = -1,
    DZ_WINDOW_UNREACHABLE = -2
};

/* Pure host/runtime arithmetic. These functions do not access camera APIs. */
int dz_aspect_base(
    const DzSensor *sensor,
    double aspect,
    int alignment,
    DzWindow *out_window
);

int dz_window_for_zoom(
    const DzSensor *sensor,
    double aspect,
    double zoom,
    int alignment,
    DzWindow *out_window
);

double dz_zoom_for_window(const DzWindow *base, const DzWindow *window);
double dz_megapixels(const DzWindow *window);
int dz_is_aligned(const DzWindow *window, int alignment);

#ifdef __cplusplus
}
#endif

#endif
