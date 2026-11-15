#version 330
#extension GL_ARB_separate_shader_objects : require

#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
#include <minecraft:fog.glsl>
#include <minecraft:sample_lightmap.glsl>
#endif

#include <minecraft:dynamictransforms.glsl>
#include <minecraft:projection.glsl>

layout(location = 0) in vec3 Position;
layout(location = 1) in vec4 Color;
layout(location = 2) in vec2 UV0;
#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
layout(location = 3) in ivec2 UV2;
#endif

#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
uniform sampler2D Sampler2;
layout(location = 0) out float sphericalVertexDistance;
layout(location = 1) out float cylindricalVertexDistance;
#endif

layout(location = 2) out vec4 vertexColor;
layout(location = 3) out vec2 texCoord0;

uniform sampler2D Sampler0;
layout(location = 4) flat out int fpvMode;
layout(location = 5) flat out float fpvNoise;
layout(location = 6) out vec2 fpvScreen;

int fpvCorner() {
    ivec2 pixel = ivec2(floor(UV0 * vec2(textureSize(Sampler0, 0))));
    for (int y = -1; y <= 0; y++) {
        for (int x = -1; x <= 0; x++) {
            ivec2 samplePixel = pixel + ivec2(x, y);
            if (any(lessThan(samplePixel, ivec2(0))) || any(greaterThanEqual(samplePixel, textureSize(Sampler0, 0)))) continue;
            ivec4 value = ivec4(round(texelFetch(Sampler0, samplePixel, 0) * 255.0));
            if (value.r == 13 && value.g == 37 && value.b >= 217 && value.b <= 220 && value.a == 1) {
                return value.b - 217;
            }
        }
    }
    return -1;
}

void main() {
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);

#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
    sphericalVertexDistance = fog_spherical_distance(Position);
    cylindricalVertexDistance = fog_cylindrical_distance(Position);
    vertexColor = Color * sample_lightmap(Sampler2, UV2);
#else
    vertexColor = Color;
#endif
    texCoord0 = UV0;
    fpvMode = 0;
    fpvNoise = 0.0;
    fpvScreen = vec2(0.0);
#ifdef IS_GUI
    fpvMode = 0;
    fpvNoise = 0.0;
    fpvScreen = vec2(0.0);
    ivec3 code = ivec3(round(Color.rgb * 255.0));
    if (code.r != 254 || code.g > 8 || ProjMat[3][3] != 1.0) return;
    int corner = fpvCorner();
    if (corner < 0) return;
    fpvMode = code.g == 0 ? 2 : 1;
    vertexColor = vec4(1.0, 1.0, 1.0, Color.a);
    if (fpvMode == 2) {
        fpvScreen = vec2(corner >= 2 ? 1.0 : 0.0, corner == 1 || corner == 2 ? 1.0 : 0.0);
        gl_Position.xy = (fpvScreen * vec2(2.0, -2.0) + vec2(-1.0, 1.0)) * gl_Position.w;
        fpvNoise = float(code.b) / 255.0;
        return;
    }
    vec2 size = vec2(2.0 / ProjMat[0][0], -2.0 / ProjMat[1][1]);
    vec2 pixel = (gl_Position.xy / gl_Position.w * vec2(0.5, -0.5) + 0.5) * size;
    vec2 local = pixel - floor(size * 0.5) - vec2(0.0, 10.0);
    vec2 anchor = vec2(18.0, 18.0);
    if (code.g == 2) anchor = vec2(floor(size.x * 0.5), 40.0);
    if (code.g == 3) anchor = vec2(size.x - 18.0, 18.0);
    if (code.g == 4) anchor = vec2(18.0, floor(size.y * 0.5));
    if (code.g == 5) anchor = vec2(size.x - 18.0, floor(size.y * 0.5));
    if (code.g == 6) anchor = vec2(18.0, size.y - 30.0);
    if (code.g == 7) anchor = vec2(size.x - 18.0, size.y - 30.0);
    if (code.g == 8) anchor = vec2(floor(size.x * 0.5), size.y - 56.0);
    gl_Position.xy = ((anchor + local) / size * vec2(2.0, -2.0) + vec2(-1.0, 1.0)) * gl_Position.w;
#endif
}
