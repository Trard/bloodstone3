#version 330
#extension GL_ARB_separate_shader_objects : require

// Can't moj_import in things used during startup, when resource packs don't exist.
// This is a copy of dynamicimports.glsl and projection.glsl
layout(std140) uniform DynamicTransforms {
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
};
layout(std140) uniform Projection {
    mat4 ProjMat;
};

layout(location = 0) in vec3 Position;
layout(location = 1) in vec2 UV0;
layout(location = 2) in vec4 Color;

layout(location = 0) out vec2 texCoord0;
layout(location = 1) out vec4 vertexColor;

uniform sampler2D Sampler0;

void main() {
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);
    if ((textureSize(Sampler0, 0) == ivec2(1280, 720) || textureSize(Sampler0, 0) == ivec2(1920, 1080))
        && all(equal(ivec4(round(texelFetch(Sampler0, ivec2(0), 0) * 255.0)), ivec4(19, 78, 231, 0)))) {
        vec2 guiSize = round(vec2(2.0 / ProjMat[0][0], -2.0 / ProjMat[1][1]));
        vec2 shift = floor((guiSize - 15.0) * 0.5) + 7.5 - guiSize * 0.5;
        vec2 offset = vec2(shift.x * ProjMat[0][0], shift.y * ProjMat[1][1]);
        vec2 overscan = abs(offset) + 4.0 / vec2(textureSize(Sampler0, 0));
        gl_Position.xy = gl_Position.xy * (1.0 + overscan) + offset * gl_Position.w;
    }

    texCoord0 = UV0;
    vertexColor = Color;
}
