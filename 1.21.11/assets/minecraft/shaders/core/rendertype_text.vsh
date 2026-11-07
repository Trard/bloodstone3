#version 330

#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>
#moj_import <minecraft:projection.glsl>

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in ivec2 UV2;

uniform sampler2D Sampler2;
uniform sampler2D Sampler0;

out float sphericalVertexDistance;
out float cylindricalVertexDistance;
out vec4 vertexColor;
out vec2 texCoord0;
out vec2 bseScreenPosition;
flat out int bseLetterbox;
flat out int bseScare;
flat out int bseCameraPhase;
flat out int bseCameraSeed;
flat out int invasionBranding;
flat out ivec2 invasionBrandingOrigin;

flat out int fpvMode;
flat out float fpvNoise;
out vec2 fpvScreen;
out vec2 bloodScreenUV;
flat out float bloodClosure;

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

void evApplyFpv() {
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
}

bool bloodEyelidMarker() {
    ivec2 size = textureSize(Sampler0, 0);
    ivec2 offsets[4] = ivec2[4](ivec2(0, 0), ivec2(0, 4), ivec2(4, 4), ivec2(4, 0));
    ivec2 origin = ivec2(round(UV0 * vec2(size))) - offsets[gl_VertexID % 4];
    if (any(lessThan(origin, ivec2(0))) || any(greaterThanEqual(origin + ivec2(3), size))) return false;
    ivec4 a = ivec4(round(texelFetch(Sampler0, origin, 0) * 255.0));
    ivec4 b = ivec4(round(texelFetch(Sampler0, origin + ivec2(3, 0), 0) * 255.0));
    ivec4 c = ivec4(round(texelFetch(Sampler0, origin + ivec2(0, 3), 0) * 255.0));
    ivec4 d = ivec4(round(texelFetch(Sampler0, origin + ivec2(3, 3), 0) * 255.0));
    return a == ivec4(173, 41, 227, 255) && b == ivec4(19, 211, 97, 255)
        && c == ivec4(61, 137, 239, 255) && d == ivec4(229, 83, 31, 255);
}

void main() {
    bloodClosure = -1.0;
    bloodScreenUV = vec2(0.0);
    gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);
    sphericalVertexDistance = fog_spherical_distance(Position);
    cylindricalVertexDistance = fog_cylindrical_distance(Position);
    vertexColor = Color * texelFetch(Sampler2, UV2 / 16, 0);
    texCoord0 = UV0;
    bseScreenPosition = vec2(0.0);
    bseLetterbox = 0;
    bseScare = 0;
    bseCameraPhase = -1;
    bseCameraSeed = 0;
    invasionBranding = 0;
    invasionBrandingOrigin = ivec2(0);
    evApplyFpv();
    if (fpvMode != 0) return;

    ivec3 bloodMarker = ivec3(round(Color.rgb * 255.0));
    if (bloodMarker.r == 1 && bloodMarker.g == 2 && bloodMarker.b >= 1 && bloodMarker.b <= 11 && bloodEyelidMarker()) {
        vec2 bloodCorners[4] = vec2[4](vec2(-1.0, 1.0), vec2(-1.0, -1.0), vec2(1.0, -1.0), vec2(1.0, 1.0));
        vec2 bloodCorner = bloodCorners[gl_VertexID % 4];
        gl_Position = vec4(bloodCorner, -0.999, 1.0);
        bloodScreenUV = bloodCorner;
        bloodClosure = float(bloodMarker.b - 1) / 10.0;
        sphericalVertexDistance = 0.0;
        cylindricalVertexDistance = 0.0;
        vertexColor = vec4(1.0);
        return;
    }

    // Only the dedicated bse:cutscene_letterbox title uses this marker.
    // Orthographic projection excludes world text / text displays entirely.
    bool marker = all(lessThan(abs(Color.rgb * 255.0 - vec3(253.0, 126.0, 1.0)), vec3(0.25)));
    if (marker && abs(ProjMat[3][3] - 1.0) < 0.001) {
        // Glyph vertices are TL, BL, BR, TR, regardless of font/GUI scale.
        const vec2 corners[4] = vec2[4](
            vec2(-1.0, 1.0), vec2(-1.0, -1.0),
            vec2(1.0, -1.0), vec2(1.0, 1.0)
        );
        bseScreenPosition = corners[gl_VertexID % 4];
        gl_Position = vec4(bseScreenPosition, 0.0, 1.0);
        bseLetterbox = 1;
    }
    // Dedicated scare fonts: a full-viewport background plus 4x4 portrait tiles.
    // The RGB marker encodes tile coordinates, not a tint. Other fonts stay vanilla.
    ivec3 tag = ivec3(round(Color.rgb * 255.0));
    bool cameraOff = tag.r == 251 && tag.g == 90 && tag.b >= 0 && tag.b < 3;
    bool cameraNoise = tag.r == 251 && tag.g == 91 && tag.b >= 0 && tag.b < 64;
    if (abs(ProjMat[3][3] - 1.0) < 0.001 && (cameraOff || cameraNoise)) {
        const vec2 cameraQuad[4] = vec2[4](vec2(-1,1),vec2(-1,-1),vec2(1,-1),vec2(1,1));
        bseScreenPosition = cameraQuad[gl_VertexID % 4];
        gl_Position = vec4(bseScreenPosition, 0.0, 1.0);
        bseCameraPhase = cameraOff ? tag.b : 3;
        bseCameraSeed = tag.b;
        vertexColor = vec4(1.0, 1.0, 1.0, Color.a);
    }
    bool background = tag == ivec3(252, 99, 99);
    bool portrait = tag.r == 252 && tag.g >= 100 && tag.g <= 103 && tag.b >= 100 && tag.b <= 103;
    if (abs(ProjMat[3][3] - 1.0) < 0.001 && (background || portrait)) {
        const vec2 quad[4] = vec2[4](vec2(0,0),vec2(0,1),vec2(1,1),vec2(1,0));
        vec2 uv = quad[gl_VertexID % 4];
        vec2 point = vec2(uv.x * 2.0 - 1.0, 1.0 - uv.y * 2.0);
        if (portrait) {
            uv = (vec2(tag.g - 100, tag.b - 100) + uv) / 4.0;
            point = vec2(uv.x * 2.0 - 1.0, 1.0 - uv.y * 2.0);
            float aspect = abs(ProjMat[1][1] / ProjMat[0][0]);
            // Fit a square portrait without stretching or cropping its face.
            point *= vec2(0.96 / max(1.0, aspect), 0.96 * min(1.0, aspect));
        }
        gl_Position = vec4(point, background ? 0.05 : 0.0, 1.0);
        bseScare = 1;
        vertexColor = vec4(1.0, 1.0, 1.0, Color.a);
    }
    // Reserved ascent in bloodinvasion:overlay/*, sent only through the action bar.
    // Leave normal GUI text, world labels and every vanilla boss bar untouched.
    if (abs(ProjMat[3][3] - 1.0) < 0.001) {
        vec4 position = ModelViewMat * vec4(Position, 1.0);
        float guiHeight = 2.0 / abs(ProjMat[1][1]);
        float markerY = position.y - guiHeight - 16384.0;
        if (markerY >= -96.0 && markerY <= 0.0) {
            // Action-bar origin: height - 68 - 4; HUD origin: 3 GUI pixels (no logo space).
            position.y -= 16384.0 + guiHeight - 75.0;
            gl_Position = ProjMat * position;
            sphericalVertexDistance = 0.0;
            cylindricalVertexDistance = 0.0;
        }
        float logoY = position.y - guiHeight - 32768.0;
        if (logoY >= -80.0 && logoY <= 0.0) {
            float guiWidth = 2.0 / abs(ProjMat[0][0]);
            const vec2 corners[4] = vec2[4](vec2(0,0), vec2(0,1), vec2(1,1), vec2(1,0));
            invasionBranding = 1;
            invasionBrandingOrigin = ivec2(floor(UV0 * vec2(textureSize(Sampler0, 0))
                - corners[gl_VertexID % 4] * vec2(254.98, 38.98)));
            // Center the logo above the timer, leaving a five-pixel gap.
            position.xy = vec2((guiWidth - 85.0) * 0.5, 4.0)
                + corners[gl_VertexID % 4] * vec2(85.0, 13.0);
            gl_Position = ProjMat * position;
            sphericalVertexDistance = 0.0;
            cylindricalVertexDistance = 0.0;
        }
    }
}
