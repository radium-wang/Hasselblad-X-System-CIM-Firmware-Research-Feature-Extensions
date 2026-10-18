#include "digital_zoom.h"

#include <limits.h>
#include <math.h>
#include <stddef.h>

static int valid_alignment(int alignment) {
    return alignment > 0;
}

static int valid_sensor(const DzSensor *sensor) {
    return sensor != NULL
        && sensor->width_px > 0
        && sensor->height_px > 0
        && isfinite(sensor->width_mm)
        && sensor->width_mm > 0.0
        && isfinite(sensor->height_mm)
        && sensor->height_mm > 0.0
        && sensor->cfa_quad > 0;
}

static int greatest_common_divisor(int left, int right) {
    while (right != 0) {
        int remainder = left % right;
        left = right;
        right = remainder;
    }
    return left;
}

static int effective_alignment(const DzSensor *sensor, int requested) {
    int divisor;
    long long combined;
    if (!valid_sensor(sensor) || !valid_alignment(requested)) {
        return 0;
    }
    divisor = greatest_common_divisor(sensor->cfa_quad, requested);
    combined = (long long)(sensor->cfa_quad / divisor) * (long long)requested;
    return combined <= INT_MAX ? (int)combined : 0;
}

static int align_down(double value, int alignment) {
    return (int)(floor(value / (double)alignment) * (double)alignment);
}

static int centre_window(
    const DzSensor *sensor,
    int width,
    int height,
    int alignment,
    DzWindow *out_window
) {
    int x;
    int y;
    if (!valid_sensor(sensor) || !valid_alignment(alignment) || out_window == NULL) {
        return DZ_INVALID_ARGUMENT;
    }
    alignment = effective_alignment(sensor, alignment);
    if (!valid_alignment(alignment)) {
        return DZ_INVALID_ARGUMENT;
    }
    if (width <= 0 || height <= 0 || width % alignment || height % alignment) {
        return DZ_INVALID_ARGUMENT;
    }
    if (width > sensor->width_px || height > sensor->height_px) {
        return DZ_WINDOW_UNREACHABLE;
    }
    x = align_down((sensor->width_px - width) / 2.0, alignment);
    y = align_down((sensor->height_px - height) / 2.0, alignment);
    if (x < 0 || y < 0 || x + width > sensor->width_px || y + height > sensor->height_px) {
        return DZ_WINDOW_UNREACHABLE;
    }
    out_window->x = x;
    out_window->y = y;
    out_window->width = width;
    out_window->height = height;
    return DZ_OK;
}

int dz_aspect_base(
    const DzSensor *sensor,
    double aspect,
    int alignment,
    DzWindow *out_window
) {
    double native_aspect;
    int width;
    int height;
    if (!valid_sensor(sensor) || !valid_alignment(alignment) || out_window == NULL) {
        return DZ_INVALID_ARGUMENT;
    }
    alignment = effective_alignment(sensor, alignment);
    if (!valid_alignment(alignment)) {
        return DZ_INVALID_ARGUMENT;
    }
    if (!isfinite(aspect) || aspect <= 0.0) {
        return DZ_INVALID_ARGUMENT;
    }
    native_aspect = (double)sensor->width_px / (double)sensor->height_px;
    if (aspect >= native_aspect) {
        width = align_down(sensor->width_px, alignment);
        height = align_down(width / aspect, alignment);
    } else {
        height = align_down(sensor->height_px, alignment);
        width = align_down(height * aspect, alignment);
    }
    if (width < alignment || height < alignment) {
        return DZ_WINDOW_UNREACHABLE;
    }
    return centre_window(sensor, width, height, alignment, out_window);
}

double dz_zoom_for_window(const DzWindow *base, const DzWindow *window) {
    double base_diag;
    double window_diag;
    if (base == NULL || window == NULL
        || base->width <= 0 || base->height <= 0
        || window->width <= 0 || window->height <= 0) {
        return NAN;
    }
    base_diag = hypot((double)base->width, (double)base->height);
    window_diag = hypot((double)window->width, (double)window->height);
    return base_diag / window_diag;
}

int dz_window_for_zoom(
    const DzSensor *sensor,
    double aspect,
    double zoom,
    int alignment,
    DzWindow *out_window
) {
    DzWindow base;
    DzWindow candidate;
    int height;
    int width;
    int status;
    if (!isfinite(zoom) || zoom < 1.0 || zoom > 2.0 || out_window == NULL) {
        return DZ_INVALID_ARGUMENT;
    }
    if (!valid_sensor(sensor) || !valid_alignment(alignment)) {
        return DZ_INVALID_ARGUMENT;
    }
    alignment = effective_alignment(sensor, alignment);
    if (!valid_alignment(alignment)) {
        return DZ_INVALID_ARGUMENT;
    }
    status = dz_aspect_base(sensor, aspect, alignment, &base);
    if (status != DZ_OK) {
        return status;
    }
    if (zoom <= 1.0) {
        *out_window = base;
        return DZ_OK;
    }

    height = base.height - alignment;
    while (height >= alignment) {
        width = align_down(height * aspect, alignment);
        if (width > base.width) {
            width = align_down(base.width, alignment);
            height = align_down(width / aspect, alignment);
        }
        if (width < alignment || height < alignment) {
            break;
        }
        status = centre_window(sensor, width, height, alignment, &candidate);
        if (status == DZ_OK && dz_zoom_for_window(&base, &candidate) >= zoom - 1e-12) {
            *out_window = candidate;
            return DZ_OK;
        }
        height -= alignment;
    }
    return DZ_WINDOW_UNREACHABLE;
}

double dz_megapixels(const DzWindow *window) {
    if (window == NULL || window->width <= 0 || window->height <= 0) {
        return NAN;
    }
    return ((double)window->width * (double)window->height) / 1000000.0;
}

int dz_is_aligned(const DzWindow *window, int alignment) {
    if (window == NULL || !valid_alignment(alignment)) {
        return 0;
    }
    return window->x % alignment == 0
        && window->y % alignment == 0
        && window->width % alignment == 0
        && window->height % alignment == 0;
}
