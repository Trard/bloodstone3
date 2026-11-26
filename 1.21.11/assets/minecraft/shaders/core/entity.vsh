#version 330

#moj_import <minecraft:light.glsl>
#moj_import <minecraft:fog.glsl>
#moj_import <minecraft:dynamictransforms.glsl>
#moj_import <minecraft:projection.glsl>

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in ivec2 UV1;
in ivec2 UV2;
in vec3 Normal;

uniform sampler2D Sampler1;
uniform sampler2D Sampler2;

out float sphericalVertexDistance;
out float cylindricalVertexDistance;
#ifdef PER_FACE_LIGHTING
out vec4 vertexPerFaceColorBack;
out vec4 vertexPerFaceColorFront;
#else
out vec4 vertexColor;
#endif
out vec4 lightMapColor;
out vec4 overlayColor;
out vec2 texCoord0;

uniform sampler2D Sampler0;
flat out int hornFacet;
out vec4 hornPlane;
out vec3 hornView;
out vec3 hornUp;

vec3 hornProxy() {
    hornFacet=0;
    hornPlane=vec4(0.0); hornUp=vec3(0.0); hornView=vec3(0.0);
    if (textureSize(Sampler0,0)!=ivec2(67,69)) return Position;
    ivec3 tag=ivec3(round(texelFetch(Sampler0,ivec2(0),0).rgb*255.0));
    if (tag.rg!=ivec2(181,71) || tag.b<1 || tag.b>5) return Position;
    vec2 uv=UV0*64.0;
    if (min(abs(uv.x-7.0),abs(uv.x-13.0))>0.01 || min(abs(uv.y-13.0),abs(uv.y-20.0))>0.01) return Position;
    hornFacet=tag.b;
    vec2 p=uv-vec2(10.0,16.0);
    vec4 bounds=vec4((3.0-p.x)/1.6,(3.0+p.x)/1.6,(3.85-p.y)/0.45,(2.5+p.y)/1.25);
    float height=hornFacet==5 ? 1.0 : bounds[hornFacet-1];
    vec3 outPos=Position+normalize(Normal)*(height*14.0*1.15/16.0);
    hornPlane=vec4((ModelViewMat*vec4(Position,1.0)).xyz,1.0);
    hornView=(ModelViewMat*vec4(outPos,1.0)).xyz;
    hornUp=mat3(ModelViewMat)*Normal;
    return outPos;
}

void main() {
    vec3 pos=hornProxy();
    gl_Position = ProjMat * ModelViewMat * vec4(pos, 1.0);

    sphericalVertexDistance = fog_spherical_distance(Position);
    cylindricalVertexDistance = fog_cylindrical_distance(Position);

#ifdef PER_FACE_LIGHTING
    vec2 light = minecraft_compute_light(Light0_Direction, Light1_Direction, Normal);
    vertexPerFaceColorBack = minecraft_mix_light_separate(-light, Color);
    vertexPerFaceColorFront = minecraft_mix_light_separate(light, Color);
#elif defined(NO_CARDINAL_LIGHTING)
    vertexColor = Color;
#else
    vertexColor = minecraft_mix_light(Light0_Direction, Light1_Direction, Normal, Color);
#endif
#ifndef EMISSIVE
    lightMapColor = texelFetch(Sampler2, UV2 / 16, 0);
#endif
    overlayColor = texelFetch(Sampler1, UV1, 0);

    texCoord0 = UV0;
#ifdef APPLY_TEXTURE_MATRIX
    texCoord0 = (TextureMat * vec4(UV0, 0.0, 1.0)).xy;
#endif
}
