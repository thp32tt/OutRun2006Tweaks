#include "vr/game/sprite_queue_tail_proof.hpp"
using OutRunVR::SpriteQueue::FirstVerifiedAppendedNode;
using OutRunVR::SpriteQueue::FirstVerifiedAppendedNodeOnStableRoot;
struct Node { Node* next_0=nullptr; Node* tail_4=nullptr; };
constexpr bool Validate()
{
    Node root{}, a{}, b{}, c{}, foreignRoot{}, foreign{};
    root.next_0=&a;root.tail_4=&c;
    a.next_0=&b;b.next_0=&c;
    // Stable root: before=a, after=c means b is first new node.
    if(FirstVerifiedAppendedNodeOnStableRoot(
           &root,&root,&a,&c,560)!=&b)return false;
    // Native producer rebuilt the priority root but reused a tail node.
    // The old root's pointer cannot authorize another root's list.
    foreignRoot.next_0=&a;foreignRoot.tail_4=&c;
    // The old tail-only helper WOULD accept b, because this new root
    // contains the reused tail address. Root identity is essential.
    if(FirstVerifiedAppendedNode(&foreignRoot,&a,&c,560)!=&b)return false;
    if(FirstVerifiedAppendedNodeOnStableRoot(
           &root,&foreignRoot,&a,&c,560))return false;
    // Previously empty sentinel becomes the first active node.
    if(FirstVerifiedAppendedNodeOnStableRoot(
           &root,&root,&root,&c,560)!=&a)return false;
    // Unlinked old tail must never be dereferenced by the helper.
    foreign.next_0=&a;
    if(FirstVerifiedAppendedNodeOnStableRoot(
           &root,&root,&foreign,&c,560))return false;
    // New tail is not in the live chain; reject foreign output.
    if(FirstVerifiedAppendedNodeOnStableRoot(
           &root,&root,&a,&foreign,560))return false;
    if(FirstVerifiedAppendedNodeOnStableRoot(
           static_cast<Node*>(nullptr),&root,&a,&c,560))return false;
    if(FirstVerifiedAppendedNodeOnStableRoot(
           &root,static_cast<Node*>(nullptr),&a,&c,560))return false;
    // Bounded scan must not spin on a cyclic or excessively long queue.
    c.next_0=&a;
    if(FirstVerifiedAppendedNodeOnStableRoot(
           &root,&root,&a,&foreign,4))return false;
    if(FirstVerifiedAppendedNodeOnStableRoot(
           &root,&root,&a,&c,0))return false;
    return true;
}
static_assert(Validate(), "original root-stability provenance contract");
int main(){return Validate()?0:1;}