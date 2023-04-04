# What I have found so far:

## NUP file:

A simple data container (model+spline+texture+material).

```cpp
struct Header{
    char ident[4];
    int32_t size; // Negative file size
    uint32_t version; // Not confirmed
    uint32_t zero; // Always zero?
};
```

After header come chunks.

```cpp
struct Chunk{
    char ident[4];
    uint32_t size; // Includes Chunk structure
};
```

Immediately followed by chunk data, chunks are always padded to 16 bytes boundary, chunk size includes padding.

### Known chunks

* NTBL - Name table.
* INST - Instance data (model id + flags + matrix).
* SPEC - "Spec" spec data, same as INST but also contains object name, used for "entities" like destructible objects,
  puzzles and etc.
* TST0 - Texture block, contains all used textures.
* OBJ0 - Contains model/particle info
* INID - Not yet fully understood, contains uint16_t array of same size as INST.
* TAS0 - Animated texture info.
* MS00 - Material info, also contains vertex format.
* SST0 - Splines.
* VBIB - Vertices and indices buffers.

### Chunk structures

Here are all known structures

#### NTBL

```cpp
struct NTBL{
    uint32_t size;
    char name_table[size];
};
```

All name offsets are offsets from start of `name_table`.

#### INST

```cpp
struct Instance{
    float matrix[16]; // Need to be transposed for blender
    uint32_t mesh_id; // Need and'ed with 0x000FFFFF. Top 3 nibbles are probably some sort of re-use flag.
    uint32_t flags; // Known flags: 0x1 - Hidden, 0x20 - Interactable/not-static.
    uint32_t unk1;
    uint32_t unk2;
};

struct INST{
    uint32_t count;
    uint32_t unk;
    Instance instances[count];
};

```

#### SPEC

```cpp
struct Entity{
    float matrix[16]; // In engine this data is replaced with matrix from INST, however data that is stored is already copy of it????
    uint32_t instance_id;
    uint32_t name_offset;
    uint32_t unk2;
    uint32_t unk3;
};

struct SPEC{
    uint32_t count;
    uint32_t unk;
    Entity entities[count];
    pad_to(16);

};
```

#### TST0

```cpp
struct Index{
   uint32_t width;
   uint32_t height;
   uint32_t unk2;
   uint32_t pixel_format;
   uint32_t offset;
};


struct TST0{
    uint32_t index_count;
    uint32_t data_size;
    uint32_t index_offset;
    uint32_t texture_data_offset; // Relative offsets (from &index_count) to Index array.
    uint32_t raw_textures_size; // Relative offsets (from &index_count) to raw texture data.
};
```
#### TAS0
```cpp

struct AnimatedTexture{ 
    uint32_t unk;
    uint32_t unk1;
    uint32_t frame_start; // Offset into all_frames array.
    uint16_t frame_count;
    uint16_t unk2;  
    uint32_t material_id;  
    uint32_t unk3;
    uint32_t name_offset;
    uint32_t other_name_offset;    
};

struct TAS0{
    uint32_t count;
    uint32_t zero;
    AnimatedTexture textues[count];
    uint32_t frame_count;
    uint16_t all_frames[frame_count];
};
```

#### MS00
```cpp
struct VertexFormat{
    uint32_t b0:1;
    uint32_t b1:1;
    uint32_t normal:1;
    uint32_t packed_normal:1;
    uint32_t tangent:1;
    uint32_t packed_tangent:1;
    uint32_t binormal:1;
    uint32_t packed_binormal:1;
    uint32_t vcolor:1;
    uint32_t vcolor1_0:1;
    uint32_t vcolor1_1:1;
    uint32_t uv_count:3;
    uint32_t blend_weights:1;
    uint32_t packed_blend_weights:1;
    uint32_t blend_indices:1;
    uint32_t packed_blend_indices:1;
    uint32_t force_packed_normal0:1;
    uint32_t b19:1;
    uint32_t b20:1;
    uint32_t b21:1;
    uint32_t position2:1;
    uint32_t force_packed_normal1:1;
    uint32_t force_packed_tangent:1;
    uint32_t b25:1;
    uint32_t b26:1;
    uint32_t b27:1;
    uint32_t b28:1;
    uint32_t b29:1;
    uint32_t b30:1;
    uint32_t b31:1;
};

struct Material{
    uint8_t zeros[48];
    int32_t mone;
    uint8_t zeros1[12];
    uint32_t flags;
    uint32_t unk;
    uint8_t zeros2[12];
    float diffuse_color[4]; // Not confirmed.
    uint8_t unk1[88];
    uint32_t texture_id0;
    uint32_t texture_id1;
    uint32_t texture_id2;
    uint32_t texture_id3;
    uint8_t unk2[236]; // Contains floats and bunch on unknown data.
    VertexFormat vertex_format;
    uint8_t zeros3[88];
};

struct Ms00{
    uint32_t count;
    uint32_t zero;
    Material materials[count];
};
```

#### OBJ0
```cpp
struct OBJ0{
    uint32_t count;
    uint32_t zero;
    Container containers[count];
};

struct Container{
  uint32_t type;
  uint32_t unk[3];
  uint32_t flags;
  // Data depends on a flag, so read text bellow first. 
  // ...
  // ...
  float bbox_min[3];
  float bbox_max[3];
  uint32_t unk1[2];
};
```
Then based on flags it's either a model or particles containers.

If flag is not zero and greater than 0, and less then 2, then it's a particles.

```cpp
struct Particle{
    float position[3];
    float scale[2]; 
    uint8_t color; //from 0 to 127. So don't forget to remap it.
};

struct ParticleGroup{
    uint32_t zeros[2];
    uint32_t material_id;
    uint32_t unk[2];
    uint32_t count;
    uint32_t zero;
    Particle particles[count];
};

struct Particle{
    uint32_t count;
    // If contaier type has second bit set, then it's a part of some vector, otherwise unsed 2 floats.
    float unk_vec[2]; // Target vector is 3d, but they only store X and Y.
    ParticleGroup groups[count];

};
```
Otherwise, it's a model container
```cpp
struct Strip{
    uint32_t unk;
    uint16_t indices_count;
    uint16_t indices_count_dup; // Duplicate value.
    uint32_t unk1[15];
    uint32_t indices_offset; // Offset into indices array, not a byte offset, it's item offset.
    uint32_t polygon_count; // Polygon count including degenerate polygons.
};

struct Model{
    uint32_t zeros[2];
    uint32_t material_id;
    uint32_t zero;
    uint32_t vertex_count;
    uint32_t vertex_count_dup; // Duplicated value.
    uint32_t unk;
    uint32_t zeros1[4];
    uint32_t strips_offset; // Relative to itself.
    uint32_t index_block_id;
    uint32_t zero1;
    uint32_t vertex_block_count; //Not confirmed
    uint32_t vertex_blocks[9]; //Always nine??? Real count in vertex_block_count.
    uint32_t unk1[7];
    uint32_t vertex_size;
    uint32_t unk2[3];
    
    // strips_offset usually points here. There no models with more than 1 strip. So my data may be wrong.
    // Strips are stored as linked list, where first value is point to next, followed by Split struct.
    // struct size depends on strip data, so you must read strip here or skip them one by one.
    
    Strip strips[...]// Read note above.

};

struct Models{
    uint32_t count;
    float unk_vec[3];
    uint32_t unk[3];
    Model models[count];
};
```

#### VBIB
```cpp
struct BufferBlock{
    uint32_t size;
    uint32_t id;
    uint32_t offset; // Relative to (vertex/index)buffer offset from VBIB
};

struct VBIB{
  uint32_t vertex_block_count;
  uint32_t index_block_count;
  
  uint32_t total_buffer_size;
  
  uint32_t vertex_blocks_offset; // Relative to start of a chunk data
  uint32_t vertex_buffer_offset; // Relative to start of a chunk data
  uint32_t vertex_buffer_size;
  
  uint32_t index_blocks_offset; // Relative to start of a chunk data
  uint32_t index_buffer_offset; // Relative to start of a chunk data
  uint32_t index_buffer_size;
  
  uint32_t zero;
  // At their respective block offsets.
  BufferBlock vertex_blocks[vertex_block_count];
  BufferBlock index_blocks[vertex_block_count];
};
```